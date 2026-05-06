"""
EIS Property Values — Three-Layer Audit Tool
=============================================
Compares property data across three layers:

  LAYER 1 (RDL vs SQL):   TagProperties-rdl.xlsx  <->  project_core.property_value
  LAYER 2 (SQL vs CSV):   project_core.property_value  <->  file-010 + file-011

Concept routing (RDL Property Concept column):
  Functional          -> expected in file-010 (TAG_NAME, PROPERTY_NAME)
  Physical            -> expected in file-011 (EQUIPMENT_NUMBER, PROPERTY_NAME)
  Functional Physical -> expected in BOTH file-010 AND file-011
  Common              -> excluded from validation

Dev usage (F5 in VS Code — no args needed):
    Edit DEV_* paths below, then run.

CLI usage:
    python scripts/debug_rdl_property_audit.py \\
        --rdl     "path/to/TagProperties-rdl.xlsx" \\
        --csv010  "path/to/JDAW-KVE-E-JA-6944-00001-010-A38.CSV" \\
        --csv011  "path/to/JDAW-KVE-E-JA-6944-00001-011-A38.CSV" \\
        --out     "rdl_audit_report.md"
        [--no-db]

Output:
    Markdown report with executive summary, DB state, and full gap lists.
    Exit code 0 always (audit tool, not a CI blocker).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import namedtuple
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import time

import pandas as pd


# ---------------------------------------------------------------------------
# Dev defaults — edit these when running locally
# CLI args override these values
# ---------------------------------------------------------------------------

DEV_RDL_PATH = Path(r"C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\JDE-Power-BI\_master\data\TagProperties-rdl.xlsx")
DEV_CSV010   = Path(r"C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\EIS\Export for Shell\May-26\CSV\eis_export_A38_20260505_0928\JDAW-KVE-E-JA-6944-00001-010-A38.CSV")
DEV_CSV011   = Path(r"C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\EIS\Export for Shell\May-26\CSV\eis_export_A38_20260505_0928\JDAW-KVE-E-JA-6944-00001-011-A38.CSV")
DEV_OUTPUT   = Path(r"C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\EIS\Export for Shell\May-26\rdl_audit_report.md")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TAG_CONCEPTS   = {"Functional", "Functional Physical"}
EQUIP_CONCEPTS = {"Physical", "Functional Physical"}
SKIP_CONCEPTS  = {"Common"}

# RDL column names (exact column headers in TagProperties-rdl.xlsx)
COL_TAG_NAME      = "Tag Name"
COL_RDL_PROP_ID   = "RDL Property Id"    # = ontology_core.property.code
COL_RDL_PROP_NAME = "RDL Property Name"  # = ontology_core.property.name = CSV PROPERTY_NAME
COL_RDL_CONCEPT   = "RDL Property Concept"
COL_PROP_VALUE    = "Property Value"
COL_PROP_UOM      = "Property UoM"
COL_ENTITY_MSG    = "Entity Message"
COL_RAM_CATEGORY  = "RAM Property Category"

EQUIP_PREFIX = "equip_"  # lower-cased for startswith check
TAG_FILTER: str | None = None  # set at runtime via --tag


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    """Normalize property name for fuzzy key matching.

    Removes all punctuation/separator characters (hyphens, dashes, slashes,
    underscores, dots) and collapses whitespace, then lowercases.

    Examples:
        'Actuation-Closing'  -> 'actuation closing'
        'ACTUATION - CLOSING' -> 'actuation closing'
        'seat material'      -> 'seat material'
        'SEAT MATERIAL'      -> 'seat material'
        'N/A'               -> 'n a'   (acceptable — not used as a lookup key)
    """
    s = s.strip().lower()
    # Replace hyphens, en-dashes, em-dashes, slashes, underscores, dots
    # with a single space, then collapse multiple spaces
    s = re.sub(r'[\-–—/_\.]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


SqlRow = namedtuple(
    "SqlRow",
    ["tag_name", "prop_code", "prop_name", "class_name",
     "mapping_concept", "prop_value", "prop_uom"]
)

CsvEntry = namedtuple("CsvEntry", ["prop_value", "prop_uom"])

@dataclass
class RdlSqlGap:
    tag_name: str
    property_name: str
    concept: str
    issue: str   # SQL_MISSING | SQL_VALUE_MISMATCH | SQL_UOM_MISMATCH | SQL_NA_BLANK | SQL_EXTRA
    rdl_value: str
    rdl_uom: str
    sql_value: str
    sql_uom: str


@dataclass
class CsvGap:
    tag_name: str
    property_name: str
    concept: str
    layer: str   # "010" | "011"
    issue: str   # CSV_MISSING | CSV_VALUE_MISMATCH | CSV_UOM_MISMATCH | CSV_NA_BLANK
                 # CSV_WRONG_FILE | CSV_DUPLICATE | EXTRA_UNKNOWN_TAG | EXTRA_UNKNOWN_PROP
    sql_value: str
    sql_uom: str
    csv_value: str
    csv_uom: str


@dataclass
class RdlCsvGap:
    tag_name: str
    property_name: str
    concept: str
    layer: str          # "010" | "011" | "010+011"
    issue: str          # RDL_CSV_MISSING | RDL_CSV_VALUE_MISMATCH | RDL_CSV_UOM_MISMATCH | RDL_CSV_NA_BLANK
    rdl_value: str
    rdl_uom: str
    csv_value: str
    csv_uom: str


@dataclass
class AuditSummary:
    # RDL facts
    rdl_row_count_pre_filter: int = 0
    total_rdl_tag_props: int = 0      # Functional + Functional Physical
    total_rdl_equip_props: int = 0    # Physical + Functional Physical
    total_rdl_both_props: int = 0     # Functional Physical only
    tags_in_rdl: int = 0

    # SQL facts (from live query)
    sql_total_rows: int = 0
    sql_unique_tags: int = 0
    sql_unique_properties: int = 0
    sql_by_concept: List[Tuple[str, int]] = field(default_factory=list)
    sql_top_properties: List[Tuple[str, int]] = field(default_factory=list)
    sql_unavailable: bool = False
    sql_error_msg: str = ""
    sql_l2_tag_count: int = 0         # sql rows with Functional or FP concept
    sql_l2_equip_count: int = 0       # sql rows with Physical or FP concept

    # SQL_EXTRA summary (kept separate to avoid report bloat)
    sql_extra_tags: List[str] = field(default_factory=list)
    sql_extra_total_props: int = 0

    # LAYER 1 gaps (RDL vs SQL)
    rdl_sql_gaps: List[RdlSqlGap] = field(default_factory=list)

    # LAYER 2 gaps (SQL vs CSV)
    csv_gaps_010: List[CsvGap] = field(default_factory=list)
    csv_gaps_011: List[CsvGap] = field(default_factory=list)
    wrong_file_010: List[CsvGap] = field(default_factory=list)
    wrong_file_011: List[CsvGap] = field(default_factory=list)
    extra_in_010: List[CsvGap] = field(default_factory=list)
    extra_in_011: List[CsvGap] = field(default_factory=list)



    empty_property_names_010: int = 0
    empty_property_names_011: int = 0
    tags_missing_from_010: List[str] = field(default_factory=list)
    tags_missing_from_011: List[str] = field(default_factory=list)

    # LAYER 0 gaps (RDL vs CSV — no SQL required)
    rdl_csv_gaps_010: List["RdlCsvGap"] = field(default_factory=list)
    rdl_csv_gaps_011: List["RdlCsvGap"] = field(default_factory=list)
    rdl_csv_missing_tags_010: List[str] = field(default_factory=list)
    rdl_csv_missing_tags_011: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def _load_rdl(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Apply validity filters to a pre-loaded RDL DataFrame."""
    df = df_raw.copy()
    df.columns = df.columns.str.strip()
    df = df.fillna("")
    df = df[df[COL_RDL_CONCEPT].str.strip() != "Common"].copy()
    df = df[df[COL_TAG_NAME].str.strip() != ""]
    df = df[df[COL_RDL_PROP_ID].str.strip() != ""]
    df = df[df[COL_RDL_PROP_NAME].str.strip() != ""]
    return df


def _load_csv(path: Path) -> pd.DataFrame:
    """Load EIS export CSV with UTF-8 BOM encoding."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df.columns = df.columns.str.strip().str.upper()
    df = df.fillna("")
    return df


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _norm_value(val: str) -> str:
    """Normalize value: strip whitespace."""
    return val.strip()



# ---------------------------------------------------------------------------
# CSV lookup builders
# ---------------------------------------------------------------------------

def _build_export_lookup_010(
    df: pd.DataFrame,
) -> Dict[Tuple[str, str], List]:
    """Build lookup: (_norm(TAG_NAME), _norm(PROPERTY_NAME)) -> [CsvEntry, ...]"""
    lookup: Dict[Tuple[str, str], List] = {}
    tags   = df.get("TAG_NAME",           pd.Series(dtype=str)).fillna("").str.strip()
    props  = df.get("PROPERTY_NAME",      pd.Series(dtype=str)).fillna("").str.strip()
    values = df.get("PROPERTY_VALUE",     pd.Series(dtype=str)).fillna("").str.strip()
    uoms   = df.get("PROPERTY_VALUE_UOM", pd.Series(dtype=str)).fillna("").str.strip()
    for tag, prop, val, uom in zip(tags, props, values, uoms):
        lookup.setdefault((_norm(tag), _norm(prop)), []).append(CsvEntry(val, uom))
    return lookup


def _build_export_lookup_011(
    df: pd.DataFrame,
) -> Dict[Tuple[str, str], List]:
    """Build lookup: (_norm(tag_without_equip_prefix), _norm(PROPERTY_NAME)) -> [CsvEntry, ...]"""
    lookup: Dict[Tuple[str, str], List] = {}
    equips = df.get("EQUIPMENT_NUMBER",   pd.Series(dtype=str)).fillna("").str.strip()
    props  = df.get("PROPERTY_NAME",      pd.Series(dtype=str)).fillna("").str.strip()
    values = df.get("PROPERTY_VALUE",     pd.Series(dtype=str)).fillna("").str.strip()
    uoms   = df.get("PROPERTY_VALUE_UOM", pd.Series(dtype=str)).fillna("").str.strip()
    for equip, prop, val, uom in zip(equips, props, values, uoms):
        tag_part = equip[len(EQUIP_PREFIX):] if equip.lower().startswith(EQUIP_PREFIX) else equip
        lookup.setdefault((_norm(tag_part), _norm(prop)), []).append(CsvEntry(val, uom))
    return lookup


# ---------------------------------------------------------------------------
# DB — load SQL data for Layer 1 and Layer 2 reference
# ---------------------------------------------------------------------------

def _query_via_mcp(sql: str, mcp_url: str, mcp_token: str) -> list:
    """Execute SQL via pgedge MCP HTTP endpoint and return rows as list of tuples.

    MCP tool call: query_database
    Endpoint: POST {mcp_url}/tools/call
    Auth: Bearer {mcp_token}
    Response: {"content": [{"type": "text", "text": "<json string>"}]}
    """
    import json
    import urllib.request

    # JSON-RPC 2.0 request format
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "query_database",
            "arguments": {"query": sql},  # CORRECT key: "query", not "sql"
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        url=mcp_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {mcp_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    # Extract TSV content from JSON-RPC response
    # Format: {"result": {"content": [{"type": "text", "text": "TSV data"}]}}
    raw = body.get("result", {}).get("content", [{}])[0].get("text", "")
    
    if not raw:
        return []

    # Parse TSV: first line = headers, remaining lines = data rows
    tsv_lines = raw.strip().split(chr(10))  # chr(10) = newline
    if not tsv_lines:
        return []

    headers = tsv_lines[0].split(chr(9))  # chr(9) = tab
    rows = []
    for line in tsv_lines[1:]:
        if line.strip():
            values = line.split(chr(9))
            # Pad with empty strings if row is shorter than headers
            while len(values) < len(headers):
                values.append("")
            rows.append(tuple(values[:len(headers)]))

    return rows


def _load_sql_data(
    summary: AuditSummary,
    no_db: bool,
) -> tuple:
    """
    Query property_value with JOIN to property + class.

    Returns:
        (sql_index, sql_index_by_name) - two dicts for different matching strategies.
        sql_index keyed by (_norm(tag_name), _norm(prop_code)).
        sql_index_by_name keyed by (_norm(tag_name), _norm(prop_name)).
    """
    if no_db:
        summary.sql_unavailable = True
        summary.sql_error_msg = "--no-db flag set"
        return {}, {}

    try:
        import os

        mcp_url   = os.getenv("MCP_DB_URL",   "https://ai-db.adzv-pt.dev/mcp/v1")
        mcp_token = os.getenv("MCP_DB_TOKEN", "ShZzR1FkhTA7ggZRmdF8dQAcfIaD4LHs7HY88W7al5U=")

        def _exec(sql: str) -> list:
            return _query_via_mcp(sql, mcp_url, mcp_token)

        data_rows = _exec("""
            SELECT
                pv.tag_name_raw                    AS tag_name,
                p.code                             AS prop_code,
                p.name                             AS prop_name,
                c.name                             AS class_name,
                pv.mapping_concept_raw             AS mapping_concept,
                pv.property_value                  AS prop_value,
                pv.property_uom_raw                AS prop_uom
            FROM "project_core"."property_value"   AS pv
            LEFT JOIN "ontology_core"."property"   AS p ON p.id = pv.property_id
            LEFT JOIN "ontology_core"."class"      AS c ON c.id = pv.class_id
            WHERE pv.object_status = 'Active'
              AND pv.tag_name_raw IS NOT NULL
            ORDER BY pv.tag_name_raw, p.code
        """)

        stats = _exec("""
            SELECT COUNT(*) AS total,
                   COUNT(DISTINCT tag_name_raw) AS utags,
                   COUNT(DISTINCT property_id) AS uprops
            FROM project_core.property_value
            WHERE object_status = 'Active'
        """)[0]

        by_concept = _exec("""
            SELECT mapping_concept_raw, COUNT(*) AS cnt
            FROM project_core.property_value
            WHERE object_status = 'Active'
            GROUP BY mapping_concept_raw ORDER BY cnt DESC
        """)

        top_props = _exec("""
            SELECT p.name, COUNT(*) AS cnt
            FROM project_core.property_value pv
            LEFT JOIN ontology_core.property p ON p.id = pv.property_id
            WHERE pv.object_status = 'Active'
            GROUP BY p.name ORDER BY cnt DESC LIMIT 10
        """)

        summary.sql_total_rows        = int(stats[0])
        summary.sql_unique_tags       = int(stats[1])
        summary.sql_unique_properties = int(stats[2])
        summary.sql_by_concept        = [(str(r[0] or ""), int(r[1])) for r in by_concept]
        summary.sql_top_properties    = [(str(r[0] or ""), int(r[1])) for r in top_props]

        sql_index: Dict[Tuple[str, str], SqlRow] = {}
        sql_index_by_name: Dict[Tuple[str, str], SqlRow] = {}

        for tag, prop_code, prop_name, class_name, concept, prop_value, prop_uom in data_rows:
            if not tag:
                continue
            row = SqlRow(
                tag_name=(tag or "").strip(),
                prop_code=(prop_code or "").strip(),
                prop_name=(prop_name or "").strip(),
                class_name=(class_name or "").strip(),
                mapping_concept=(concept or "").strip(),
                prop_value=(prop_value or "").strip() if prop_value is not None else "",
                prop_uom=(prop_uom or "").strip() if prop_uom is not None else "",
            )
            key_by_code = (_norm(row.tag_name), _norm(row.prop_code))
            key_by_name = (_norm(row.tag_name), _norm(row.prop_name))
            sql_index.setdefault(key_by_code, row)
            sql_index_by_name.setdefault(key_by_name, row)

        return sql_index, sql_index_by_name

    except Exception as exc:  # noqa: BLE001
        summary.sql_unavailable = True
        summary.sql_error_msg = str(exc)
        return {}, {}


# ---------------------------------------------------------------------------
# LAYER 0: RDL vs CSV gap detection (direct, no SQL)
# ---------------------------------------------------------------------------

def _detect_rdl_csv_gaps(
    rdl: pd.DataFrame,
    lookup_010: Dict,
    lookup_011: Dict,
    summary: AuditSummary,
) -> None:
    """Populate summary.rdl_csv_gaps_010 and _011 by comparing RDL against CSV lookups.

    Matching: prop_name (display name) == CSV PROPERTY_NAME.
    Routing: Functional->010, Physical->011, Functional Physical->both.
    """
    for _, row in rdl.iterrows():
        tag_name  = row.get(COL_TAG_NAME, "").strip()
        prop_name = row.get(COL_RDL_PROP_NAME, "").strip()
        concept   = row.get(COL_RDL_CONCEPT, "").strip()
        rdl_val   = row.get(COL_PROP_VALUE, "").strip()
        rdl_uom   = row.get(COL_PROP_UOM, "").strip()

        if TAG_FILTER and _norm(tag_name) != TAG_FILTER.lower():
            continue
        debug = TAG_FILTER is not None

        if not tag_name or not prop_name:
            continue
        if concept in SKIP_CONCEPTS:
            if debug:
                print(f"  SKIPPED: concept {concept!r} is in SKIP_CONCEPTS")
            continue

        if debug:
            print(f"\n[RDL ROW] tag={tag_name!r}  prop_name={prop_name!r}  "
                  f"concept={concept!r}  rdl_val={rdl_val!r}  rdl_uom={rdl_uom!r}")

        def check_lookup(
            lookup_key: Tuple[str, str],
            lookup: Dict,
            layer_id: str,
        ) -> None:
            if debug:
                print(f"  [check_lookup] layer={layer_id}  key={lookup_key!r}")
                sample = [k for k in lookup if k == lookup_key][:3]
                print(f"    matching keys: {sample}")

            csv_entries = lookup.get(lookup_key, [])

            if debug:
                print(f"    csv_entries: {csv_entries!r}")

            if not csv_entries:
                gap = RdlCsvGap(
                    tag_name=tag_name,
                    property_name=prop_name,
                    concept=concept,
                    layer=layer_id,
                    issue="RDL_CSV_MISSING",
                    rdl_value=rdl_val,
                    rdl_uom=rdl_uom,
                    csv_value="<missing>",
                    csv_uom="<missing>",
                )
                if layer_id == "010":
                    summary.rdl_csv_gaps_010.append(gap)
                else:
                    summary.rdl_csv_gaps_011.append(gap)
                return

            for entry in csv_entries:
                csv_val = entry.prop_value
                csv_uom = entry.prop_uom
                rdl_is_na = rdl_val.upper() in ("NA", "N/A")
                csv_is_blank = not csv_val or csv_val.strip() == ""

                if rdl_is_na and csv_is_blank:
                    gap = RdlCsvGap(
                        tag_name=tag_name,
                        property_name=prop_name,
                        concept=concept,
                        layer=layer_id,
                        issue="RDL_CSV_NA_BLANK",
                        rdl_value=rdl_val,
                        rdl_uom=rdl_uom,
                        csv_value=csv_val,
                        csv_uom=csv_uom,
                    )
                    if layer_id == "010":
                        summary.rdl_csv_gaps_010.append(gap)
                    else:
                        summary.rdl_csv_gaps_011.append(gap)
                    continue

                if not rdl_is_na and not csv_is_blank:
                    if csv_val != rdl_val:
                        gap = RdlCsvGap(
                            tag_name=tag_name,
                            property_name=prop_name,
                            concept=concept,
                            layer=layer_id,
                            issue="RDL_CSV_VALUE_MISMATCH",
                            rdl_value=rdl_val,
                            rdl_uom=rdl_uom,
                            csv_value=csv_val,
                            csv_uom=csv_uom,
                        )
                        if layer_id == "010":
                            summary.rdl_csv_gaps_010.append(gap)
                        else:
                            summary.rdl_csv_gaps_011.append(gap)

                if rdl_uom and csv_uom:
                    if csv_uom != rdl_uom:
                        gap = RdlCsvGap(
                            tag_name=tag_name,
                            property_name=prop_name,
                            concept=concept,
                            layer=layer_id,
                            issue="RDL_CSV_UOM_MISMATCH",
                            rdl_value=rdl_val,
                            rdl_uom=rdl_uom,
                            csv_value=csv_val,
                            csv_uom=csv_uom,
                        )
                        if layer_id == "010":
                            summary.rdl_csv_gaps_010.append(gap)
                        else:
                            summary.rdl_csv_gaps_011.append(gap)

        # Routing based on concept (explicit checks - no dead-code elif)
        key = (_norm(tag_name), _norm(prop_name))
        if concept == "Functional":
            check_lookup(key, lookup_010, "010")
        elif concept == "Physical":
            check_lookup(key, lookup_011, "011")
        elif concept == "Functional Physical":
            check_lookup(key, lookup_010, "010")
            check_lookup(key, lookup_011, "011")
        elif debug:
            print(f"  [WARN] unknown concept {concept!r} for {tag_name}/{prop_name}")




# LAYER 1: RDL vs SQL gap detection
# ---------------------------------------------------------------------------

def _detect_rdl_sql_gaps(
    rdl: pd.DataFrame,
    sql_index: Dict[Tuple[str, str], SqlRow],
    summary: AuditSummary,
) -> None:
    """Populate summary.rdl_sql_gaps by comparing RDL rows against sql_index (keyed by prop_code)."""
    rdl_keys: set = set()

    for _, row in rdl.iterrows():
        tag_name  = row.get(COL_TAG_NAME, "").strip()
        prop_id   = row.get(COL_RDL_PROP_ID, "").strip()
        concept   = row.get(COL_RDL_CONCEPT, "").strip()
        rdl_val   = row.get(COL_PROP_VALUE, "").strip()
        rdl_uom   = row.get(COL_PROP_UOM, "").strip()

        if TAG_FILTER and _norm(tag_name) != TAG_FILTER.lower():
            continue

        if not tag_name or not prop_id:
            continue
        if concept in SKIP_CONCEPTS:
            continue

        if concept in TAG_CONCEPTS:
            summary.total_rdl_tag_props += 1
        if concept in EQUIP_CONCEPTS:
            summary.total_rdl_equip_props += 1
        if concept == "Functional Physical":
            summary.total_rdl_both_props += 1

        key = (_norm(tag_name), _norm(prop_id))
        rdl_keys.add(key)
        sql_hit = sql_index.get(key)

        if sql_hit is None:
            summary.rdl_sql_gaps.append(RdlSqlGap(
                tag_name=tag_name,
                property_name=prop_id,
                concept=concept,
                issue="SQL_MISSING",
                rdl_value=rdl_val,
                rdl_uom=rdl_uom,
                sql_value="",
                sql_uom="",
            ))
        else:
            _sdv = sql_hit.prop_value if sql_hit.prop_value else "(NULL)"
            _sdu = sql_hit.prop_uom if sql_hit.prop_uom else "(NULL)"
            if rdl_val.upper() in ("NA", "N/A") and not sql_hit.prop_value.strip():
                summary.rdl_sql_gaps.append(RdlSqlGap(
                    tag_name=tag_name,
                    property_name=prop_id,
                    concept=concept,
                    issue="SQL_NA_BLANK",
                    rdl_value=rdl_val,
                    rdl_uom=rdl_uom,
                    sql_value=_sdv,
                    sql_uom=_sdu,
                ))
            elif rdl_val and sql_hit.prop_value and sql_hit.prop_value.upper() != rdl_val.upper():
                summary.rdl_sql_gaps.append(RdlSqlGap(
                    tag_name=tag_name,
                    property_name=prop_id,
                    concept=concept,
                    issue="SQL_VALUE_MISMATCH",
                    rdl_value=rdl_val,
                    rdl_uom=rdl_uom,
                    sql_value=_sdv,
                    sql_uom=_sdu,
                ))
            else:
                sql_uom_norm = (sql_hit.prop_uom or "").upper()
                rdl_uom_norm = rdl_uom.upper()
                if sql_uom_norm != rdl_uom_norm and not (sql_uom_norm == "" and rdl_uom_norm == ""):
                    summary.rdl_sql_gaps.append(RdlSqlGap(
                        tag_name=tag_name,
                        property_name=prop_id,
                        concept=concept,
                        issue="SQL_UOM_MISMATCH",
                        rdl_value=rdl_val,
                        rdl_uom=rdl_uom,
                        sql_value=_sdv,
                        sql_uom=_sdu,
                    ))

    summary.tags_in_rdl = len({k[0] for k in rdl_keys})

    # SQL_EXTRA: in sql_index but not in RDL
    sql_extra_by_tag: Dict[str, List[RdlSqlGap]] = {}
    for key, sql_row in sql_index.items():
        if sql_row.mapping_concept in SKIP_CONCEPTS:
            continue
        if key not in rdl_keys:
            gap = RdlSqlGap(
                tag_name=sql_row.tag_name,
                property_name=sql_row.prop_code,
                concept=sql_row.mapping_concept,
                issue="SQL_EXTRA",
                rdl_value="",
                rdl_uom="",
                sql_value=sql_row.prop_value or "(NULL)",
                sql_uom=sql_row.prop_uom or "(NULL)",
            )
            sql_extra_by_tag.setdefault(sql_row.tag_name, []).append(gap)

    summary.sql_extra_tags = sorted(sql_extra_by_tag.keys())
    summary.sql_extra_total_props = sum(len(v) for v in sql_extra_by_tag.values())
    capped = 0
    for gaps_for_tag in sql_extra_by_tag.values():
        if capped >= 200:
            break
        for gap in gaps_for_tag:
            if capped >= 200:
                break
            summary.rdl_sql_gaps.append(gap)
            capped += 1


# ---------------------------------------------------------------------------
# LAYER 2: SQL vs CSV gap detection
# ---------------------------------------------------------------------------

def _detect_sql_csv_gaps(
    sql_index_by_name: Dict[Tuple[str, str], SqlRow],
    lookup_010: Dict,
    lookup_011: Dict,
    summary: AuditSummary,
) -> None:
    """Populate summary.csv_gaps_010/011 by comparing sql_index_by_name against CSV lookups."""
    if not sql_index_by_name:
        return

    tags_needing_010: set = set()
    tags_needing_011: set = set()

    for key, sql_row in sql_index_by_name.items():
        concept = sql_row.mapping_concept
        if TAG_FILTER and _norm(sql_row.tag_name) != TAG_FILTER.lower():
            continue
        if concept in SKIP_CONCEPTS:
            continue

        prop_key = (_norm(sql_row.tag_name), _norm(sql_row.prop_name))

        def _check_csv(lookup: Dict, layer: str, gap_list: list, tag_set: set) -> None:
            tag_set.add(_norm(sql_row.tag_name))
            hits = lookup.get(prop_key)
            if hits is None:
                gap_list.append(CsvGap(
                    tag_name=sql_row.tag_name,
                    property_name=sql_row.prop_name,
                    concept=concept,
                    layer=layer,
                    issue="CSV_MISSING",
                    sql_value=sql_row.prop_value or "(NULL)",
                    sql_uom=sql_row.prop_uom or "(NULL)",
                    csv_value="",
                    csv_uom="",
                ))
                return
            entry = hits[0]
            csv_val = entry.prop_value
            csv_uom = entry.prop_uom
            _sdv = sql_row.prop_value or "(NULL)"
            _sdu = sql_row.prop_uom or "(NULL)"
            sql_val_norm = (sql_row.prop_value or "").upper()
            csv_val_norm = csv_val.upper()
            sql_uom_norm = (sql_row.prop_uom or "").upper()
            csv_uom_norm = csv_uom.upper()
            if sql_val_norm in ("NA", "N/A") and csv_val.strip() == "":
                gap_list.append(CsvGap(
                    tag_name=sql_row.tag_name, property_name=sql_row.prop_name,
                    concept=concept, layer=layer, issue="CSV_NA_BLANK",
                    sql_value=_sdv, sql_uom=_sdu, csv_value=csv_val, csv_uom=csv_uom,
                ))
            elif sql_val_norm != csv_val_norm and not (sql_val_norm == "" and csv_val_norm == ""):
                gap_list.append(CsvGap(
                    tag_name=sql_row.tag_name, property_name=sql_row.prop_name,
                    concept=concept, layer=layer, issue="CSV_VALUE_MISMATCH",
                    sql_value=_sdv, sql_uom=_sdu, csv_value=csv_val, csv_uom=csv_uom,
                ))
            elif sql_uom_norm != csv_uom_norm and not (sql_uom_norm == "" and csv_uom_norm == ""):
                gap_list.append(CsvGap(
                    tag_name=sql_row.tag_name, property_name=sql_row.prop_name,
                    concept=concept, layer=layer, issue="CSV_UOM_MISMATCH",
                    sql_value=_sdv, sql_uom=_sdu, csv_value=csv_val, csv_uom=csv_uom,
                ))

        if concept == "Functional":
            summary.sql_l2_tag_count += 1
            _check_csv(lookup_010, "010", summary.csv_gaps_010, tags_needing_010)
        elif concept == "Physical":
            summary.sql_l2_equip_count += 1
            _check_csv(lookup_011, "011", summary.csv_gaps_011, tags_needing_011)
        elif concept == "Functional Physical":
            summary.sql_l2_tag_count += 1
            summary.sql_l2_equip_count += 1
            _check_csv(lookup_010, "010", summary.csv_gaps_010, tags_needing_010)
            _check_csv(lookup_011, "011", summary.csv_gaps_011, tags_needing_011)

    tags_found_010 = {k[0] for k in lookup_010}
    summary.tags_missing_from_010 = sorted(t for t in tags_needing_010 if t not in tags_found_010)

    tags_found_011 = {k[0] for k in lookup_011}
    summary.tags_missing_from_011 = sorted(t for t in tags_needing_011 if t not in tags_found_011)


# ---------------------------------------------------------------------------
# WRONG_FILE and EXTRA detection (uses sql_index as reference)
# ---------------------------------------------------------------------------

def _detect_wrong_and_extra(
    df010: pd.DataFrame,
    df011: pd.DataFrame,
    sql_index_by_name: Dict[Tuple[str, str], SqlRow],
    summary: AuditSummary,
) -> None:
    """Detect properties in the wrong CSV file or absent from sql_index entirely."""
    if not sql_index_by_name:
        return

    sql_tag_set = {k[0] for k in sql_index_by_name}

    for _, row in df010.iterrows():
        tag  = _norm(row.get("TAG_NAME", ""))
        prop = _norm(row.get("PROPERTY_NAME", ""))
        if not tag or not prop:
            continue
        sql_row = sql_index_by_name.get((tag, prop))
        if sql_row is None:
            issue = "EXTRA_UNKNOWN_TAG" if tag not in sql_tag_set else "EXTRA_UNKNOWN_PROP"
            summary.extra_in_010.append(CsvGap(
                tag_name=row.get("TAG_NAME", ""),
                property_name=row.get("PROPERTY_NAME", ""),
                concept="",
                layer="010",
                issue=issue,
                sql_value="",
                sql_uom="",
                csv_value=row.get("PROPERTY_VALUE", ""),
                csv_uom=row.get("PROPERTY_VALUE_UOM", ""),
            ))
        elif sql_row.mapping_concept == "Physical":
            summary.wrong_file_010.append(CsvGap(
                tag_name=row.get("TAG_NAME", ""),
                property_name=row.get("PROPERTY_NAME", ""),
                concept=sql_row.mapping_concept,
                layer="010",
                issue="CSV_WRONG_FILE",
                sql_value=sql_row.prop_value or "(NULL)",
                sql_uom=sql_row.prop_uom or "(NULL)",
                csv_value=row.get("PROPERTY_VALUE", ""),
                csv_uom=row.get("PROPERTY_VALUE_UOM", ""),
            ))

    for _, row in df011.iterrows():
        equip   = row.get("EQUIPMENT_NUMBER", "")
        tag_raw = equip[len(EQUIP_PREFIX):] if equip.lower().startswith(EQUIP_PREFIX) else equip
        tag  = _norm(tag_raw)
        prop = _norm(row.get("PROPERTY_NAME", ""))
        if not tag or not prop:
            continue
        sql_row = sql_index_by_name.get((tag, prop))
        if sql_row is None:
            issue = "EXTRA_UNKNOWN_TAG" if tag not in sql_tag_set else "EXTRA_UNKNOWN_PROP"
            summary.extra_in_011.append(CsvGap(
                tag_name=tag_raw,
                property_name=row.get("PROPERTY_NAME", ""),
                concept="",
                layer="011",
                issue=issue,
                sql_value="",
                sql_uom="",
                csv_value=row.get("PROPERTY_VALUE", ""),
                csv_uom=row.get("PROPERTY_VALUE_UOM", ""),
            ))
        elif sql_row.mapping_concept == "Functional":
            summary.wrong_file_011.append(CsvGap(
                tag_name=tag_raw,
                property_name=row.get("PROPERTY_NAME", ""),
                concept=sql_row.mapping_concept,
                layer="011",
                issue="CSV_WRONG_FILE",
                sql_value=sql_row.prop_value or "(NULL)",
                sql_uom=sql_row.prop_uom or "(NULL)",
                csv_value=row.get("PROPERTY_VALUE", ""),
                csv_uom=row.get("PROPERTY_VALUE_UOM", ""),
            ))



# ---------------------------------------------------------------------------
# Structural checks (empty names only — duplicates handled via raw lookup)
# ---------------------------------------------------------------------------

def _check_structural(
    df010: pd.DataFrame,
    df011: pd.DataFrame,
    summary: AuditSummary,
) -> None:
    """Check for empty property names in export files."""
    if "PROPERTY_NAME" in df010.columns:
        summary.empty_property_names_010 = int((df010["PROPERTY_NAME"].str.strip() == "").sum())

    if "PROPERTY_NAME" in df011.columns:
        summary.empty_property_names_011 = int((df011["PROPERTY_NAME"].str.strip() == "").sum())


# ---------------------------------------------------------------------------
# Markdown rendering helpers
# ---------------------------------------------------------------------------

def _escape(s: str, max_len: int = 120) -> str:
    """Escape pipe chars and truncate for Markdown table cell."""
    s = str(s).replace("|", "｜")
    return s[:max_len] + "…" if len(s) > max_len else s


def _issue_icon(issue: str) -> str:
    if "RDL_CSV_MISSING" in issue:
        return "🚫"
    if "SQL_MISSING" in issue:
        return "⛔"
    if "CSV_MISSING" in issue:
        return "❌"
    if "DUPLICATE" in issue:
        return "🔁"
    if "VALUE_MISMATCH" in issue:
        return "⚠️"
    if "UOM_MISMATCH" in issue:
        return "📐"
    if "NA_BLANK" in issue:
        return "🔕"
    if "WRONG_FILE" in issue:
        return "🔀"
    if "EXTRA" in issue:
        return "➕"
    if "SQL_EXTRA" in issue:
        return "➕"
    return "ℹ️"


def _render_rdl_sql_gap_table(gaps: List[RdlSqlGap]) -> List[str]:
    lines = [
        "| # | Icon | Tag | Property Code | Concept | Issue | RDL Value | RDL UoM | SQL Value | SQL UoM |",
        "|---|------|-----|---------------|---------|-------|-----------|---------|-----------|---------|",
    ]
    for i, g in enumerate(gaps, start=1):
        lines.append(
            f"| {i} | {_issue_icon(g.issue)} | `{_escape(g.tag_name)}` "
            f"| `{_escape(g.property_name)}` | {g.concept} | **{g.issue}** "
            f"| {_escape(g.rdl_value)} | {_escape(g.rdl_uom)} "
            f"| {_escape(g.sql_value)} | {_escape(g.sql_uom)} |"
        )
    return lines


def _render_csv_gap_table(gaps: List[CsvGap]) -> List[str]:
    lines = [
        "| # | Icon | Tag | Property | Concept | Issue | SQL Value | SQL UoM | CSV Value | CSV UoM |",
        "|---|------|-----|----------|---------|-------|-----------|---------|-----------|---------|",
    ]
    for i, g in enumerate(gaps, start=1):
        lines.append(
            f"| {i} | {_issue_icon(g.issue)} | `{_escape(g.tag_name)}` "
            f"| `{_escape(g.property_name)}` | {g.concept} | **{g.issue}** "
            f"| {_escape(g.sql_value)} | {_escape(g.sql_uom)} "
            f"| {_escape(g.csv_value)} | {_escape(g.csv_uom)} |"
        )
    return lines




def _render_rdl_csv_gap_table(gaps: List[RdlCsvGap]) -> List[str]:
    """Render LAYER 0 gap table (RDL vs CSV)."""
    lines = [
        "| # | Icon | Tag | Property Code | Concept | Issue | RDL Value | RDL UoM | CSV Value | CSV UoM |",
        "|---|------|-----|---------------|---------|-------|-----------|---------|-----------|---------|",
    ]
    for i, g in enumerate(gaps, start=1):
        lines.append(
            f"| {i} | {_issue_icon(g.issue)} | `{_escape(g.tag_name)}` "
            f"| `{_escape(g.property_name)}` | {g.concept} | **{g.issue}** "
            f"| {_escape(g.rdl_value)} | {_escape(g.rdl_uom)} "
            f"| {_escape(g.csv_value)} | {_escape(g.csv_uom)} |"
        )
    return lines


def render_report(
    summary: AuditSummary,
    rdl_path: Path,
    csv010_path: Path,
    csv011_path: Path,
) -> str:
    lines: List[str] = []

    lines.append("# EIS Property Values — Three-Layer Audit Report")
    lines.append("")
    lines.append(f"**RDL Reference:** `{rdl_path}`  ")
    lines.append(f"**File 010 (Tag Property Values):** `{csv010_path}`  ")
    lines.append(f"**File 011 (Equipment Property Values):** `{csv011_path}`  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Executive Summary ────────────────────────────────────────────────────
    n_sql_missing    = sum(1 for g in summary.rdl_sql_gaps if g.issue == "SQL_MISSING")
    n_sql_mismatch   = sum(1 for g in summary.rdl_sql_gaps if g.issue == "SQL_VALUE_MISMATCH")
    n_sql_uom        = sum(1 for g in summary.rdl_sql_gaps if g.issue == "SQL_UOM_MISMATCH")
    n_sql_na         = sum(1 for g in summary.rdl_sql_gaps if g.issue == "SQL_NA_BLANK")
    n_sql_extra      = summary.sql_extra_total_props   # use the full count, not the 200-row cap
    n_csv_miss_010   = sum(1 for g in summary.csv_gaps_010 if g.issue == "CSV_MISSING")
    n_csv_miss_011   = sum(1 for g in summary.csv_gaps_011 if g.issue == "CSV_MISSING")
    n_csv_mm_010     = sum(1 for g in summary.csv_gaps_010 if g.issue == "CSV_VALUE_MISMATCH")
    n_csv_mm_011     = sum(1 for g in summary.csv_gaps_011 if g.issue == "CSV_VALUE_MISMATCH")
    n_csv_uom_010    = sum(1 for g in summary.csv_gaps_010 if g.issue == "CSV_UOM_MISMATCH")
    n_csv_uom_011    = sum(1 for g in summary.csv_gaps_011 if g.issue == "CSV_UOM_MISMATCH")
    n_csv_na_010     = sum(1 for g in summary.csv_gaps_010 if g.issue == "CSV_NA_BLANK")
    n_csv_na_011     = sum(1 for g in summary.csv_gaps_011 if g.issue == "CSV_NA_BLANK")
    n_rdl_ref        = summary.total_rdl_tag_props + summary.total_rdl_equip_props - summary.total_rdl_both_props

    lines.append("## Executive Summary")
    lines.append("")
    # LAYER 0 metrics (calculated for Executive Summary)
    n_l0_miss_010   = len([g for g in summary.rdl_csv_gaps_010 if g.issue == "RDL_CSV_MISSING"])
    n_l0_miss_011   = len([g for g in summary.rdl_csv_gaps_011 if g.issue == "RDL_CSV_MISSING"])
    n_l0_mm_010     = len([g for g in summary.rdl_csv_gaps_010 if g.issue == "RDL_CSV_VALUE_MISMATCH"])
    n_l0_mm_011     = len([g for g in summary.rdl_csv_gaps_011 if g.issue == "RDL_CSV_VALUE_MISMATCH"])
    n_l0_uom_010    = len([g for g in summary.rdl_csv_gaps_010 if g.issue == "RDL_CSV_UOM_MISMATCH"])
    n_l0_uom_011    = len([g for g in summary.rdl_csv_gaps_011 if g.issue == "RDL_CSV_UOM_MISMATCH"])
    n_l0_na_010     = len([g for g in summary.rdl_csv_gaps_010 if g.issue == "RDL_CSV_NA_BLANK"])
    n_l0_na_011     = len([g for g in summary.rdl_csv_gaps_011 if g.issue == "RDL_CSV_NA_BLANK"])

    lines.append("| Metric | LAYER 0 (RDL vs CSV) | LAYER 1 (RDL vs SQL) | LAYER 2 (SQL vs CSV 010) | LAYER 2 (SQL vs CSV 011) |")
    lines.append("|--------|---------------------|---------------------|--------------------------|--------------------------|")
    lines.append(f"| Reference rows | — | {n_rdl_ref:,} | {summary.sql_l2_tag_count:,} | {summary.sql_l2_equip_count:,} |")
    lines.append(f"| 🚫 RDL_CSV_MISSING | **{n_l0_miss_010+n_l0_miss_011:,}** | — | — | — |")
    lines.append(f"| ⚠️ RDL_CSV_VALUE_MISMATCH | {n_l0_mm_010+n_l0_mm_011:,} | — | — | — |")
    lines.append(f"| 📐 RDL_CSV_UOM_MISMATCH | {n_l0_uom_010+n_l0_uom_011:,} | — | — | — |")
    lines.append(f"| 🔕 RDL_CSV_NA_BLANK | {n_l0_na_010+n_l0_na_011:,} | — | — | — |")

    # LAYER 1 metrics — show "N/A (no-db)" when DB unavailable
    sql_col = "N/A (no-db)" if summary.sql_unavailable else f"**{n_sql_missing:,}**"
    lines.append(f"| ⛔ SQL_MISSING (critical) | — | {sql_col} | — | — |")
    sql_col = "N/A (no-db)" if summary.sql_unavailable else f"{n_sql_mismatch:,}"
    lines.append(f"| ⚠️ SQL_VALUE_MISMATCH | — | {sql_col} | — | — |")
    sql_col = "N/A (no-db)" if summary.sql_unavailable else f"{n_sql_uom:,}"
    lines.append(f"| 📐 SQL_UOM_MISMATCH | — | {sql_col} | — | — |")
    sql_col = "N/A (no-db)" if summary.sql_unavailable else f"{n_sql_na:,}"
    lines.append(f"| 🔕 SQL_NA_BLANK | — | {sql_col} | — | — |")
    sql_col = "N/A (no-db)" if summary.sql_unavailable else f"{n_sql_extra:,}"
    lines.append(f"| ➕ SQL_EXTRA | — | {sql_col} | — | — |")
    lines.append(f"| ❌ CSV_MISSING | — | — | **{n_csv_miss_010:,}** | **{n_csv_miss_011:,}** |")
    lines.append(f"| ⚠️ CSV_VALUE_MISMATCH | — | — | {n_csv_mm_010:,} | {n_csv_mm_011:,} |")
    lines.append(f"| 📐 CSV_UOM_MISMATCH | — | — | {n_csv_uom_010:,} | {n_csv_uom_011:,} |")
    lines.append(f"| 🔕 CSV_NA_BLANK | — | — | {n_csv_na_010:,} | {n_csv_na_011:,} |")
    lines.append(f"| 🔀 WRONG_FILE | — | — | {len(summary.wrong_file_010):,} | {len(summary.wrong_file_011):,} |")
    lines.append(f"| ➕ EXTRA (unknown) | — | — | {len(summary.extra_in_010):,} | {len(summary.extra_in_011):,} |")
    lines.append("")

    if n_sql_missing > 0 and not summary.sql_unavailable:
        lines.append(
            f"> ⛔ **CRITICAL:** {n_sql_missing:,} properties exist in RDL but are **MISSING from SQL database**. "
            "These were never imported. Run the import flow to fix."
        )
    csv_missing_total = n_csv_miss_010 + n_csv_miss_011
    if csv_missing_total > 0:
        lines.append(
            f"> ⚠️  {csv_missing_total:,} properties exist in SQL but are **MISSING from CSV export**. "
            "These were imported but not exported. Check EIS export filters."
        )
    lines.append("")
    lines.append(f"- {'⚠️' if summary.empty_property_names_010 > 0 else '✅'} File 010 rows with empty PROPERTY_NAME: **{summary.empty_property_names_010}**")
    lines.append(f"- {'⚠️' if summary.empty_property_names_011 > 0 else '✅'} File 011 rows with empty PROPERTY_NAME: **{summary.empty_property_names_011}**")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── DB State ─────────────────────────────────────────────────────────────
    lines.append("## DB State (live — project_core.property_value)")
    lines.append("")
    if summary.sql_unavailable:
        lines.append(f"> ⚠️ DB query unavailable: `{summary.sql_error_msg}`")
        lines.append("> Layer 1 and Layer 2 gaps are empty. Re-run without `--no-db` for full analysis.")
    else:
        lines.append("| Metric | Value |")
        lines.append("|--------|------:|")
        lines.append(f"| Total property_value rows (Active) | {summary.sql_total_rows:,} |")
        lines.append(f"| Unique tags with properties | {summary.sql_unique_tags:,} |")
        lines.append(f"| Unique distinct properties | {summary.sql_unique_properties:,} |")
        lines.append("")
        if summary.sql_by_concept:
            lines.append("**Rows by mapping_concept_raw:**")
            lines.append("")
            lines.append("| Concept | Count |")
            lines.append("|---------|------:|")
            for concept, cnt in summary.sql_by_concept:
                lines.append(f"| `{_escape(concept)}` | {cnt:,} |")
            lines.append("")
        if summary.sql_top_properties:
            lines.append("**Top 10 properties by row count:**")
            lines.append("")
            lines.append("| Property Code | Count |")
            lines.append("|---------------|------:|")
            for code, cnt in summary.sql_top_properties:
                lines.append(f"| `{_escape(code)}` | {cnt:,} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── LAYER 0: RDL vs CSV (direct, no SQL) ────────────────────────────────
    lines.append("## LAYER 0 — RDL vs CSV (Direct, no SQL)")
    lines.append("")
    lines.append("> This layer checks RDL reference values directly against CSV export files.")
    lines.append("> **SQL is not required** — useful when DB is unavailable.")
    lines.append("")

    # Calculate metrics for LAYER 0
    n_l0_miss_010   = len([g for g in summary.rdl_csv_gaps_010 if g.issue == "RDL_CSV_MISSING"])
    n_l0_miss_011   = len([g for g in summary.rdl_csv_gaps_011 if g.issue == "RDL_CSV_MISSING"])
    n_l0_mm_010     = len([g for g in summary.rdl_csv_gaps_010 if g.issue == "RDL_CSV_VALUE_MISMATCH"])
    n_l0_mm_011     = len([g for g in summary.rdl_csv_gaps_011 if g.issue == "RDL_CSV_VALUE_MISMATCH"])
    n_l0_uom_010    = len([g for g in summary.rdl_csv_gaps_010 if g.issue == "RDL_CSV_UOM_MISMATCH"])
    n_l0_uom_011    = len([g for g in summary.rdl_csv_gaps_011 if g.issue == "RDL_CSV_UOM_MISMATCH"])
    n_l0_na_010     = len([g for g in summary.rdl_csv_gaps_010 if g.issue == "RDL_CSV_NA_BLANK"])
    n_l0_na_011     = len([g for g in summary.rdl_csv_gaps_011 if g.issue == "RDL_CSV_NA_BLANK"])

    # Metrics table
    lines.append("### Metrics")
    lines.append("")
    lines.append("| Metric | vs CSV-010 | vs CSV-011 |")
    lines.append("|--------|-----------:|-----------:|")
    lines.append(f"| 🚫 RDL_CSV_MISSING | **{n_l0_miss_010:,}** | **{n_l0_miss_011:,}** |")
    lines.append(f"| ⚠️ RDL_CSV_VALUE_MISMATCH | {n_l0_mm_010:,} | {n_l0_mm_011:,} |")
    lines.append(f"| 📐 RDL_CSV_UOM_MISMATCH | {n_l0_uom_010:,} | {n_l0_uom_011:,} |")
    lines.append(f"| 🔕 RDL_CSV_NA_BLANK | {n_l0_na_010:,} | {n_l0_na_011:,} |")
    lines.append("")

    # Detailed tables for file-010
    if summary.rdl_csv_gaps_010:
        lines.append("### File-010 (Tag Property Values) Details")
        lines.append("")

        for issue_type, header in [
            ("RDL_CSV_MISSING",        "🚫 RDL_CSV_MISSING — Critical: in RDL, absent from CSV-010"),
            ("RDL_CSV_VALUE_MISMATCH", "⚠️ RDL_CSV_VALUE_MISMATCH"),
            ("RDL_CSV_UOM_MISMATCH",   "📐 RDL_CSV_UOM_MISMATCH"),
            ("RDL_CSV_NA_BLANK",       "🔕 RDL_CSV_NA_BLANK"),
        ]:
            subset = [g for g in summary.rdl_csv_gaps_010 if g.issue == issue_type]
            if not subset:
                continue
            lines.append(f"#### {header} ({len(subset):,})")
            lines.append("")
            lines.extend(_render_rdl_csv_gap_table(subset))
            lines.append("")

    # Detailed tables for file-011
    if summary.rdl_csv_gaps_011:
        lines.append("### File-011 (Equipment Property Values) Details")
        lines.append("")

        for issue_type, header in [
            ("RDL_CSV_MISSING",        "🚫 RDL_CSV_MISSING — Critical: in RDL, absent from CSV-011"),
            ("RDL_CSV_VALUE_MISMATCH", "⚠️ RDL_CSV_VALUE_MISMATCH"),
            ("RDL_CSV_UOM_MISMATCH",   "📐 RDL_CSV_UOM_MISMATCH"),
            ("RDL_CSV_NA_BLANK",       "🔕 RDL_CSV_NA_BLANK"),
        ]:
            subset = [g for g in summary.rdl_csv_gaps_011 if g.issue == issue_type]
            if not subset:
                continue
            lines.append(f"#### {header} ({len(subset):,})")
            lines.append("")
            lines.extend(_render_rdl_csv_gap_table(subset))
            lines.append("")

    if not summary.rdl_csv_gaps_010 and not summary.rdl_csv_gaps_011:
        lines.append("✅ No Layer 0 gaps found.")
        lines.append("")

    lines.append("---")
    lines.append("")

    # ── LAYER 1: RDL vs SQL ───────────────────────────────────────────────────
    lines.append("## LAYER 1 — RDL vs SQL Gaps")
    lines.append("")
    lines.append(f"> RDL after filters: **{summary.rdl_row_count_pre_filter:,}** rows pre-filter; "
                 f"**{summary.total_rdl_tag_props:,}** tag props, **{summary.total_rdl_equip_props:,}** equip props, "
                 f"**{summary.total_rdl_both_props:,}** Functional Physical (both files).")
    lines.append("")

    if summary.sql_unavailable:
        lines.append("> ⚠️ DB unavailable — Layer 1 analysis skipped.")
        lines.append("")
    elif not any(g for g in summary.rdl_sql_gaps):
        lines.append("✅ No Layer 1 gaps found.")
        lines.append("")
    else:
        for issue_type, header in [
            ("SQL_MISSING",        "⛔ SQL_MISSING — Critical: in RDL, absent from database"),
            ("SQL_VALUE_MISMATCH", "⚠️ SQL_VALUE_MISMATCH"),
            ("SQL_UOM_MISMATCH",   "📐 SQL_UOM_MISMATCH"),
            ("SQL_NA_BLANK",       "🔕 SQL_NA_BLANK"),
        ]:
            subset = [g for g in summary.rdl_sql_gaps if g.issue == issue_type]
            if not subset:
                continue
            lines.append(f"### {header} ({len(subset):,})")
            lines.append("")
            lines.extend(_render_rdl_sql_gap_table(subset))
            lines.append("")

        # SQL_EXTRA — potentially huge; show callout + capped table
        extra_subset = [g for g in summary.rdl_sql_gaps if g.issue == "SQL_EXTRA"]
        if extra_subset or summary.sql_extra_total_props > 0:
            lines.append(f"### ➕ SQL_EXTRA — In SQL but not in RDL ({summary.sql_extra_total_props:,} total)")
            lines.append("")
            n_extra_tags = len(summary.sql_extra_tags)
            tag_list = ", ".join(summary.sql_extra_tags[:50])
            if n_extra_tags > 50:
                tag_list += "…"
            lines.append(
                f"> ℹ️ **SQL_EXTRA:** {summary.sql_extra_total_props:,} properties across "
                f"{n_extra_tags:,} tags are present in SQL but not in the RDL file. "
                f"Showing first {len(extra_subset)} rows below."
            )
            if n_extra_tags > 0:
                lines.append(">")
                lines.append(f"> **Tag list:** {tag_list}")
            lines.append("")
            if extra_subset:
                lines.extend(_render_rdl_sql_gap_table(extra_subset))
                lines.append("")

    lines.append("---")
    lines.append("")

    # ── LAYER 2: SQL vs CSV 010 ───────────────────────────────────────────────
    lines.append("## LAYER 2 — SQL vs CSV 010 (Tag Property Values)")
    lines.append("")

    def _render_l2_section(
        gaps: List[CsvGap],
        wrong: List[CsvGap],
        extra: List[CsvGap],
        file_label: str,
    ) -> None:
        if summary.sql_unavailable:
            lines.append(f"> ⚠️ DB unavailable — Layer 2 {file_label} analysis skipped.")
            lines.append("")
            return

        all_empty = not gaps and not wrong and not extra
        if all_empty:
            lines.append(f"✅ No Layer 2 gaps found in {file_label}.")
            lines.append("")
            return

        for issue_type, header in [
            ("CSV_MISSING",        "❌ CSV_MISSING — In SQL, absent from export"),
            ("CSV_VALUE_MISMATCH", "⚠️ CSV_VALUE_MISMATCH"),
            ("CSV_UOM_MISMATCH",   "📐 CSV_UOM_MISMATCH"),
            ("CSV_NA_BLANK",       "🔕 CSV_NA_BLANK"),
        ]:
            subset = [g for g in gaps if g.issue == issue_type]
            if not subset:
                continue
            lines.append(f"### {header} ({len(subset):,})")
            lines.append("")
            lines.extend(_render_csv_gap_table(subset))
            lines.append("")

        dup_subset = [g for g in gaps if "DUPLICATE" in g.issue]
        if dup_subset:
            lines.append(f"### 🔁 CSV_DUPLICATE ({len(dup_subset):,})")
            lines.append("")
            lines.extend(_render_csv_gap_table(dup_subset))
            lines.append("")

        if wrong:
            lines.append(f"### 🔀 CSV_WRONG_FILE ({len(wrong):,})")
            lines.append("")
            lines.extend(_render_csv_gap_table(wrong))
            lines.append("")

        if extra:
            lines.append(f"### ➕ EXTRA ({len(extra):,})")
            lines.append("")
            lines.extend(_render_csv_gap_table(extra))
            lines.append("")

    _render_l2_section(summary.csv_gaps_010, summary.wrong_file_010, summary.extra_in_010, "file-010")

    if summary.tags_missing_from_010:
        lines.append("### Tags Missing Entirely from File 010")
        lines.append("")
        lines.append("> These tags have Functional or Functional Physical rows in SQL but zero rows in file-010.")
        lines.append("")
        for t in summary.tags_missing_from_010:
            lines.append(f"- `{t}`")
        lines.append("")

    lines.append("---")
    lines.append("")

    # ── LAYER 2: SQL vs CSV 011 ───────────────────────────────────────────────
    lines.append("## LAYER 2 — SQL vs CSV 011 (Equipment Property Values)")
    lines.append("")

    _render_l2_section(summary.csv_gaps_011, summary.wrong_file_011, summary.extra_in_011, "file-011")

    if summary.tags_missing_from_011:
        lines.append("### Tags Missing Entirely from File 011")
        lines.append("")
        lines.append("> These tags have Physical or Functional Physical rows in SQL but zero rows in file-011.")
        lines.append("")
        for t in summary.tags_missing_from_011:
            lines.append(f"- `{t}`")
        lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("---")
    lines.append("")

    # ── Legend ────────────────────────────────────────────────────────────────
    lines.append("## Legend")
    lines.append("")
    lines.append("| Icon | Code | Layer | Meaning |")
    lines.append("|------|------|-------|---------|")
    lines.append("| ⛔ | SQL_MISSING | L1 | In RDL but absent from SQL database — never imported |")
    lines.append("| ⚠️ | SQL_VALUE_MISMATCH | L1 | Value in SQL differs from RDL reference |")
    lines.append("| 📐 | SQL_UOM_MISMATCH | L1 | UoM in SQL differs from RDL reference |")
    lines.append("| 🔕 | SQL_NA_BLANK | L1 | RDL has 'NA' but SQL has empty/null |")
    lines.append("| ➕ | SQL_EXTRA | L1 | In SQL (non-Common) but not present in RDL |")
    lines.append("| ❌ | CSV_MISSING | L2 | In SQL but absent from export CSV |")
    lines.append("| ⚠️ | CSV_VALUE_MISMATCH | L2 | Value in CSV differs from SQL |")
    lines.append("| 📐 | CSV_UOM_MISMATCH | L2 | UoM in CSV differs from SQL |")
    lines.append("| 🔕 | CSV_NA_BLANK | L2 | SQL has 'NA' but CSV has empty string |")
    lines.append("| 🔁 | CSV_DUPLICATE | L2 | Same TAG_NAME/EQUIP_NUMBER + PROPERTY_NAME appears >1 time in CSV |")
    lines.append("| 🔀 | CSV_WRONG_FILE | L2 | Property in wrong file (Physical in 010 or Functional in 011) |")
    lines.append("| ➕ | EXTRA_UNKNOWN_TAG | L2 | Tag in CSV has no matching tag in SQL at all |")
    lines.append("| ➕ | EXTRA_UNKNOWN_PROP | L2 | Tag known in SQL but this property pair is not in SQL |")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Three-layer audit of EIS property value export files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--rdl",    default=None, metavar="FILE",
                   help="Path to TagProperties-rdl.xlsx")
    p.add_argument("--csv010", default=None, metavar="FILE",
                   help="Path to JDAW-...-010-*.CSV")
    p.add_argument("--csv011", default=None, metavar="FILE",
                   help="Path to JDAW-...-011-*.CSV")
    p.add_argument("--out",    default=None, metavar="FILE",
                   help="Output .md report path (default: rdl_audit_report.md in scripts/)")
    p.add_argument("--no-db", action="store_true",
                   help="Skip DB query entirely (offline mode)")
    p.add_argument(
        "--tag", default=None, metavar="TAG",
        help="Debug mode: filter ALL layers to a single tag name. "
             "Prints verbose trace for every RDL row of that tag."
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    global TAG_FILTER
    TAG_FILTER = args.tag.strip().upper() if args.tag else None
    if TAG_FILTER:
        print(f"\n⚡ DEBUG MODE — single tag filter: {TAG_FILTER}\n")

    rdl_path    = Path(args.rdl)    if args.rdl    else DEV_RDL_PATH
    csv010_path = Path(args.csv010) if args.csv010 else DEV_CSV010
    csv011_path = Path(args.csv011) if args.csv011 else DEV_CSV011
    output_path = Path(args.out)    if args.out    else DEV_OUTPUT

    print(f"RDL reference:  {rdl_path}")
    print(f"File 010 (Tag): {csv010_path}")
    print(f"File 011 (Eq):  {csv011_path}")
    print(f"Output:         {output_path}")

    for p, label in [(rdl_path, "RDL"), (csv010_path, "csv010"), (csv011_path, "csv011")]:
        if not p.exists():
            print(f"ERROR: {label} file not found: {p}")
            return 1

    print("Loading files...", flush=True)
    t0 = time.perf_counter()
    try:
        rdl_raw = pd.read_excel(rdl_path, dtype=str, na_filter=False, engine="calamine")
    except Exception:
        rdl_raw = pd.read_excel(rdl_path, dtype=str, na_filter=False)
    rdl_raw.columns = rdl_raw.columns.str.strip()
    rdl_raw = rdl_raw.fillna("")
    print(f"  RDL loaded:    {len(rdl_raw):,} rows ({time.perf_counter()-t0:.1f}s)", flush=True)

    t1 = time.perf_counter()
    rdl = _load_rdl(rdl_raw)
    print(f"  RDL filtered:  {len(rdl):,} rows ({time.perf_counter()-t1:.1f}s)", flush=True)

    t2 = time.perf_counter()
    df010 = _load_csv(csv010_path)
    print(f"  CSV-010:       {len(df010):,} rows ({time.perf_counter()-t2:.1f}s)", flush=True)

    t3 = time.perf_counter()
    df011 = _load_csv(csv011_path)
    print(f"  CSV-011:       {len(df011):,} rows ({time.perf_counter()-t3:.1f}s)", flush=True)

    summary = AuditSummary()
    summary.rdl_row_count_pre_filter = len(rdl_raw)

    # Layer 1 - load SQL data
    print("Querying DB...", end=" ", flush=True)
    sql_index, sql_index_by_name = _load_sql_data(summary, no_db=args.no_db)
    if summary.sql_unavailable:
        print(f"unavailable ({summary.sql_error_msg[:80]})")
    else:
        print(f"done. sql_index={len(sql_index):,} entries  total_active={summary.sql_total_rows:,}")

    print("LAYER 1 - RDL vs SQL...", end=" ", flush=True)
    if not summary.sql_unavailable:
        _detect_rdl_sql_gaps(rdl, sql_index, summary)
    n_l1_missing  = sum(1 for g in summary.rdl_sql_gaps if g.issue == "SQL_MISSING")
    n_l1_mismatch = sum(1 for g in summary.rdl_sql_gaps if g.issue == "SQL_VALUE_MISMATCH")
    print(f"done. SQL_MISSING={n_l1_missing:,}  SQL_MISMATCH={n_l1_mismatch:,}  SQL_EXTRA={summary.sql_extra_total_props:,}")

    print("Building CSV lookups...", end=" ", flush=True)
    lookup_010 = _build_export_lookup_010(df010)
    lookup_011 = _build_export_lookup_011(df011)
    print(f"010 keys={len(lookup_010):,}  011 keys={len(lookup_011):,}")

    print("LAYER 2 - SQL vs CSV...", end=" ", flush=True)
    _detect_sql_csv_gaps(sql_index_by_name, lookup_010, lookup_011, summary)
    n_l2_miss_010 = sum(1 for g in summary.csv_gaps_010 if g.issue == "CSV_MISSING")
    n_l2_miss_011 = sum(1 for g in summary.csv_gaps_011 if g.issue == "CSV_MISSING")
    print(f"done. CSV_MISSING_010={n_l2_miss_010:,}  CSV_MISSING_011={n_l2_miss_011:,}")

    print("LAYER 0 - RDL vs CSV (direct)...", end=" ", flush=True)
    _detect_rdl_csv_gaps(rdl, lookup_010, lookup_011, summary)
    n_l0_miss = len(summary.rdl_csv_gaps_010) + len(summary.rdl_csv_gaps_011)
    print(f"done. gaps_010={len(summary.rdl_csv_gaps_010):,}  gaps_011={len(summary.rdl_csv_gaps_011):,}")

    print("Detecting wrong-file and extra...", end=" ", flush=True)
    _detect_wrong_and_extra(df010, df011, sql_index_by_name, summary)
    print(
        f"done. WRONG_010={len(summary.wrong_file_010):,}  WRONG_011={len(summary.wrong_file_011):,}  "
        f"EXTRA_010={len(summary.extra_in_010):,}  EXTRA_011={len(summary.extra_in_011):,}"
    )

    _check_structural(df010, df011, summary)

    total_gaps = (
        len(summary.rdl_csv_gaps_010) + len(summary.rdl_csv_gaps_011)  # Layer 0
        + len(summary.rdl_sql_gaps)                                       # Layer 1
        + len(summary.csv_gaps_010) + len(summary.csv_gaps_011)          # Layer 2
        + len(summary.wrong_file_010) + len(summary.wrong_file_011)
        + len(summary.extra_in_010) + len(summary.extra_in_011)
    )

    md = render_report(summary, rdl_path, csv010_path, csv011_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")

    print(f"\nLAYER1 SQL_MISSING={n_l1_missing}  SQL_MISMATCH={n_l1_mismatch}")
    print(f"LAYER2 CSV_MISSING_010={n_l2_miss_010}  CSV_MISSING_011={n_l2_miss_011}")
    print(f"Report written to {output_path.resolve()} — {total_gaps:,} total gaps found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
