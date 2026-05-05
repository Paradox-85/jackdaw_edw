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
import sys
from collections import namedtuple
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


# ---------------------------------------------------------------------------
# Dev defaults — edit these when running locally
# CLI args override these values
# ---------------------------------------------------------------------------

DEV_RDL_PATH = Path(r"C:\path\to\TagProperties-rdl.xlsx")
DEV_CSV010   = Path(r"C:\path\to\JDAW-KVE-E-JA-6944-00001-010-A38.CSV")
DEV_CSV011   = Path(r"C:\path\to\JDAW-KVE-E-JA-6944-00001-011-A38.CSV")
DEV_OUTPUT   = Path(__file__).parent / "rdl_audit_report.md"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TAG_CONCEPTS   = {"Functional", "Functional Physical"}
EQUIP_CONCEPTS = {"Physical", "Functional Physical"}
SKIP_CONCEPTS  = {"Common", ""}

# RDL column names
COL_ENTITY_ID    = "Entity ID"             # maps to property_value.tag_name_raw
COL_RAM_PROP_CODE = "RAM Property Code"    # maps to property_value.property_code_raw
COL_RDL_CONCEPT  = "RDL Property Concept"
COL_PROP_VALUE   = "Property Value"
COL_PROP_UOM     = "Property UoM"
COL_ENTITY_MSG   = "Entity Message"
COL_RAM_CATEGORY = "RAM Property Category"

EQUIP_NUMBER_PREFIX = "Equip_"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

SqlRow = namedtuple("SqlRow", ["tag", "prop", "concept", "uom", "value"])


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

    # LAYER 1 gaps (RDL vs SQL)
    rdl_sql_gaps: List[RdlSqlGap] = field(default_factory=list)

    # LAYER 2 gaps (SQL vs CSV)
    csv_gaps_010: List[CsvGap] = field(default_factory=list)
    csv_gaps_011: List[CsvGap] = field(default_factory=list)
    wrong_file_010: List[CsvGap] = field(default_factory=list)
    wrong_file_011: List[CsvGap] = field(default_factory=list)
    extra_in_010: List[CsvGap] = field(default_factory=list)
    extra_in_011: List[CsvGap] = field(default_factory=list)
    duplicates_010: int = 0
    duplicates_011: int = 0
    empty_property_names_010: int = 0
    empty_property_names_011: int = 0
    tags_missing_from_010: List[str] = field(default_factory=list)
    tags_missing_from_011: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def _load_rdl(path: Path) -> pd.DataFrame:
    """Load TagProperties-rdl.xlsx, normalize column names, apply validity filters."""
    df = pd.read_excel(path, dtype=str)
    df = df.fillna("")
    df.columns = df.columns.str.strip()
    if COL_ENTITY_MSG in df.columns:
        df = df[df[COL_ENTITY_MSG].str.strip() != ""]
    if COL_RAM_CATEGORY in df.columns:
        df = df[~df[COL_RAM_CATEGORY].str.strip().isin({"TAG", "NF", ""})]
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

def _norm_prop_name(name: str) -> str:
    """Normalize property name for comparison: uppercase, strip, collapse spaces."""
    return " ".join(name.strip().upper().split())


def _norm_value(val: str) -> str:
    """Normalize value: strip whitespace."""
    return val.strip()


def _equip_number(tag_name: str) -> str:
    """Derive equipment number from tag name (same logic as export pipeline)."""
    return f"{EQUIP_NUMBER_PREFIX}{tag_name}"


# ---------------------------------------------------------------------------
# CSV lookup builders (unchanged from prior version)
# ---------------------------------------------------------------------------

def _build_export_lookup_010(
    df: pd.DataFrame,
) -> Dict[Tuple[str, str], List[Tuple[str, str]]]:
    """Build lookup: (TAG_NAME_upper, PROPERTY_NAME_upper) -> [(value, uom), ...]"""
    lookup: Dict[Tuple[str, str], List[Tuple[str, str]]] = {}
    for _, row in df.iterrows():
        key = (_norm_prop_name(row.get("TAG_NAME", "")),
               _norm_prop_name(row.get("PROPERTY_NAME", "")))
        val = (_norm_value(row.get("PROPERTY_VALUE", "")),
               _norm_value(row.get("PROPERTY_VALUE_UOM", "")))
        lookup.setdefault(key, []).append(val)
    return lookup


def _build_export_lookup_011(
    df: pd.DataFrame,
) -> Dict[Tuple[str, str], List[Tuple[str, str]]]:
    """Build lookup: (EQUIPMENT_NUMBER_upper, PROPERTY_NAME_upper) -> [(value, uom), ...]"""
    lookup: Dict[Tuple[str, str], List[Tuple[str, str]]] = {}
    for _, row in df.iterrows():
        key = (_norm_prop_name(row.get("EQUIPMENT_NUMBER", "")),
               _norm_prop_name(row.get("PROPERTY_NAME", "")))
        val = (_norm_value(row.get("PROPERTY_VALUE", "")),
               _norm_value(row.get("PROPERTY_VALUE_UOM", "")))
        lookup.setdefault(key, []).append(val)
    return lookup


# ---------------------------------------------------------------------------
# DB — load SQL data for Layer 1 and Layer 2 reference
# ---------------------------------------------------------------------------

def _load_sql_data(
    summary: AuditSummary,
    no_db: bool,
) -> Dict[Tuple[str, str], SqlRow]:
    """
    Query project_core.property_value and build sql_index for both layers.

    Returns:
        dict[(tag_name_upper, property_code_upper), SqlRow] — active non-Common rows.
        Populates summary.sql_* fields in-place.
    """
    if no_db:
        summary.sql_unavailable = True
        summary.sql_error_msg = "--no-db flag set"
        return {}

    try:
        import os

        import psycopg2

        dsn = os.getenv("EDW_DB_URL") or os.getenv("DATABASE_URL")
        if dsn:
            conn = psycopg2.connect(dsn, connect_timeout=10)
        else:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                dbname=os.getenv("DB_NAME", "engineering_core"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                connect_timeout=10,
            )

        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT tag_name_raw, property_code_raw, mapping_concept_raw,
                           property_uom_raw, property_value
                    FROM project_core.property_value
                    WHERE object_status = 'Active'
                      AND mapping_concept_raw NOT IN ('Common', '')
                      AND mapping_concept_raw IS NOT NULL
                """)
                data_rows = cur.fetchall()

                cur.execute("""
                    SELECT COUNT(*),
                           COUNT(DISTINCT tag_name_raw),
                           COUNT(DISTINCT property_code_raw)
                    FROM project_core.property_value
                    WHERE object_status = 'Active'
                """)
                stats = cur.fetchone()

                cur.execute("""
                    SELECT mapping_concept_raw, COUNT(*) AS cnt
                    FROM project_core.property_value
                    WHERE object_status = 'Active'
                    GROUP BY mapping_concept_raw ORDER BY cnt DESC
                """)
                by_concept = cur.fetchall()

                cur.execute("""
                    SELECT property_code_raw, COUNT(*) AS cnt
                    FROM project_core.property_value
                    WHERE object_status = 'Active'
                    GROUP BY property_code_raw ORDER BY cnt DESC LIMIT 10
                """)
                top_props = cur.fetchall()

        conn.close()

        summary.sql_total_rows       = stats[0]
        summary.sql_unique_tags      = stats[1]
        summary.sql_unique_properties = stats[2]
        summary.sql_by_concept       = [(r[0] or "", r[1]) for r in by_concept]
        summary.sql_top_properties   = [(r[0] or "", r[1]) for r in top_props]

        sql_index: Dict[Tuple[str, str], SqlRow] = {}
        for tag, prop, concept, uom, value in data_rows:
            if not tag or not prop:
                continue
            key = (tag.strip().upper(), prop.strip().upper())
            sql_index[key] = SqlRow(
                tag=tag.strip(),
                prop=prop.strip(),
                concept=(concept or "").strip(),
                uom=(uom or "").strip(),
                value=(value or "").strip(),
            )

        return sql_index

    except Exception as exc:  # noqa: BLE001
        summary.sql_unavailable = True
        summary.sql_error_msg = str(exc)
        return {}


# ---------------------------------------------------------------------------
# LAYER 1: RDL vs SQL gap detection
# ---------------------------------------------------------------------------

def _detect_rdl_sql_gaps(
    rdl: pd.DataFrame,
    sql_index: Dict[Tuple[str, str], SqlRow],
    summary: AuditSummary,
) -> None:
    """Populate summary.rdl_sql_gaps by comparing RDL rows against sql_index."""
    rdl_keys: set = set()

    for _, row in rdl.iterrows():
        entity_id = row.get(COL_ENTITY_ID, "").strip()
        prop_code = row.get(COL_RAM_PROP_CODE, "").strip()
        concept   = row.get(COL_RDL_CONCEPT, "").strip()
        rdl_val   = row.get(COL_PROP_VALUE, "").strip()
        rdl_uom   = row.get(COL_PROP_UOM, "").strip()

        if not entity_id or not prop_code:
            continue
        if concept in SKIP_CONCEPTS:
            continue

        if concept in TAG_CONCEPTS:
            summary.total_rdl_tag_props += 1
        if concept in EQUIP_CONCEPTS:
            summary.total_rdl_equip_props += 1
        if concept == "Functional Physical":
            summary.total_rdl_both_props += 1

        key = (entity_id.upper(), prop_code.upper())
        rdl_keys.add(key)
        sql_hit = sql_index.get(key)

        if sql_hit is None:
            summary.rdl_sql_gaps.append(RdlSqlGap(
                tag_name=entity_id,
                property_name=prop_code,
                concept=concept,
                issue="SQL_MISSING",
                rdl_value=rdl_val,
                rdl_uom=rdl_uom,
                sql_value="",
                sql_uom="",
            ))
        else:
            # NA_BLANK check must precede VALUE_MISMATCH
            if rdl_val.upper() in ("NA", "N/A") and (not sql_hit.value or sql_hit.value.strip() == ""):
                summary.rdl_sql_gaps.append(RdlSqlGap(
                    tag_name=entity_id,
                    property_name=prop_code,
                    concept=concept,
                    issue="SQL_NA_BLANK",
                    rdl_value=rdl_val,
                    rdl_uom=rdl_uom,
                    sql_value=sql_hit.value,
                    sql_uom=sql_hit.uom,
                ))
            elif (rdl_val and sql_hit.value
                  and sql_hit.value.upper() != rdl_val.upper()):
                summary.rdl_sql_gaps.append(RdlSqlGap(
                    tag_name=entity_id,
                    property_name=prop_code,
                    concept=concept,
                    issue="SQL_VALUE_MISMATCH",
                    rdl_value=rdl_val,
                    rdl_uom=rdl_uom,
                    sql_value=sql_hit.value,
                    sql_uom=sql_hit.uom,
                ))
            elif (rdl_uom and sql_hit.uom
                  and sql_hit.uom.upper() != rdl_uom.upper()):
                summary.rdl_sql_gaps.append(RdlSqlGap(
                    tag_name=entity_id,
                    property_name=prop_code,
                    concept=concept,
                    issue="SQL_UOM_MISMATCH",
                    rdl_value=rdl_val,
                    rdl_uom=rdl_uom,
                    sql_value=sql_hit.value,
                    sql_uom=sql_hit.uom,
                ))

    summary.tags_in_rdl = len({k[0] for k in rdl_keys})

    # SQL_EXTRA: in sql_index but not in RDL (non-Common only)
    for key, sql_row in sql_index.items():
        if sql_row.concept in SKIP_CONCEPTS:
            continue
        if key not in rdl_keys:
            summary.rdl_sql_gaps.append(RdlSqlGap(
                tag_name=sql_row.tag,
                property_name=sql_row.prop,
                concept=sql_row.concept,
                issue="SQL_EXTRA",
                rdl_value="",
                rdl_uom="",
                sql_value=sql_row.value,
                sql_uom=sql_row.uom,
            ))


# ---------------------------------------------------------------------------
# LAYER 2: SQL vs CSV gap detection
# ---------------------------------------------------------------------------

def _detect_sql_csv_gaps(
    sql_index: Dict[Tuple[str, str], SqlRow],
    lookup_010: Dict,
    lookup_011: Dict,
    summary: AuditSummary,
) -> None:
    """Populate summary.csv_gaps_010/011 by comparing sql_index against CSV lookups."""
    tags_needing_010: set = set()
    tags_needing_011: set = set()

    for key, sql_row in sql_index.items():
        concept = sql_row.concept
        if concept in SKIP_CONCEPTS:
            continue

        # ---- File-010 check (Functional + Functional Physical) ----
        if concept in TAG_CONCEPTS:
            summary.sql_l2_tag_count += 1
            tag_upper = sql_row.tag.strip().upper()
            tags_needing_010.add(tag_upper)
            key_010 = (tag_upper, sql_row.prop.strip().upper())
            hits = lookup_010.get(key_010)

            if hits is None:
                summary.csv_gaps_010.append(CsvGap(
                    tag_name=sql_row.tag,
                    property_name=sql_row.prop,
                    concept=concept,
                    layer="010",
                    issue="CSV_MISSING",
                    sql_value=sql_row.value,
                    sql_uom=sql_row.uom,
                    csv_value="",
                    csv_uom="",
                ))
            elif len(hits) > 1:
                summary.csv_gaps_010.append(CsvGap(
                    tag_name=sql_row.tag,
                    property_name=sql_row.prop,
                    concept=concept,
                    layer="010",
                    issue=f"CSV_DUPLICATE ({len(hits)} rows)",
                    sql_value=sql_row.value,
                    sql_uom=sql_row.uom,
                    csv_value=hits[0][0],
                    csv_uom=hits[0][1],
                ))
            else:
                csv_val, csv_uom = hits[0]
                # NA_BLANK check must precede VALUE_MISMATCH
                if (sql_row.value and sql_row.value.upper() in ("NA", "N/A")
                        and csv_val.strip() == ""):
                    summary.csv_gaps_010.append(CsvGap(
                        tag_name=sql_row.tag,
                        property_name=sql_row.prop,
                        concept=concept,
                        layer="010",
                        issue="CSV_NA_BLANK",
                        sql_value=sql_row.value,
                        sql_uom=sql_row.uom,
                        csv_value=csv_val,
                        csv_uom=csv_uom,
                    ))
                elif sql_row.value and csv_val and csv_val.upper() != sql_row.value.upper():
                    summary.csv_gaps_010.append(CsvGap(
                        tag_name=sql_row.tag,
                        property_name=sql_row.prop,
                        concept=concept,
                        layer="010",
                        issue="CSV_VALUE_MISMATCH",
                        sql_value=sql_row.value,
                        sql_uom=sql_row.uom,
                        csv_value=csv_val,
                        csv_uom=csv_uom,
                    ))
                elif sql_row.uom and csv_uom and csv_uom.upper() != sql_row.uom.upper():
                    summary.csv_gaps_010.append(CsvGap(
                        tag_name=sql_row.tag,
                        property_name=sql_row.prop,
                        concept=concept,
                        layer="010",
                        issue="CSV_UOM_MISMATCH",
                        sql_value=sql_row.value,
                        sql_uom=sql_row.uom,
                        csv_value=csv_val,
                        csv_uom=csv_uom,
                    ))

        # ---- File-011 check (Physical + Functional Physical) ----
        if concept in EQUIP_CONCEPTS:
            summary.sql_l2_equip_count += 1
            equip_upper = ("EQUIP_" + sql_row.tag.strip()).upper()
            tags_needing_011.add(equip_upper)
            equip_key = (equip_upper, sql_row.prop.strip().upper())
            hits = lookup_011.get(equip_key)

            if hits is None:
                summary.csv_gaps_011.append(CsvGap(
                    tag_name=sql_row.tag,
                    property_name=sql_row.prop,
                    concept=concept,
                    layer="011",
                    issue="CSV_MISSING",
                    sql_value=sql_row.value,
                    sql_uom=sql_row.uom,
                    csv_value="",
                    csv_uom="",
                ))
            elif len(hits) > 1:
                summary.csv_gaps_011.append(CsvGap(
                    tag_name=sql_row.tag,
                    property_name=sql_row.prop,
                    concept=concept,
                    layer="011",
                    issue=f"CSV_DUPLICATE ({len(hits)} rows)",
                    sql_value=sql_row.value,
                    sql_uom=sql_row.uom,
                    csv_value=hits[0][0],
                    csv_uom=hits[0][1],
                ))
            else:
                csv_val, csv_uom = hits[0]
                if (sql_row.value and sql_row.value.upper() in ("NA", "N/A")
                        and csv_val.strip() == ""):
                    summary.csv_gaps_011.append(CsvGap(
                        tag_name=sql_row.tag,
                        property_name=sql_row.prop,
                        concept=concept,
                        layer="011",
                        issue="CSV_NA_BLANK",
                        sql_value=sql_row.value,
                        sql_uom=sql_row.uom,
                        csv_value=csv_val,
                        csv_uom=csv_uom,
                    ))
                elif sql_row.value and csv_val and csv_val.upper() != sql_row.value.upper():
                    summary.csv_gaps_011.append(CsvGap(
                        tag_name=sql_row.tag,
                        property_name=sql_row.prop,
                        concept=concept,
                        layer="011",
                        issue="CSV_VALUE_MISMATCH",
                        sql_value=sql_row.value,
                        sql_uom=sql_row.uom,
                        csv_value=csv_val,
                        csv_uom=csv_uom,
                    ))
                elif sql_row.uom and csv_uom and csv_uom.upper() != sql_row.uom.upper():
                    summary.csv_gaps_011.append(CsvGap(
                        tag_name=sql_row.tag,
                        property_name=sql_row.prop,
                        concept=concept,
                        layer="011",
                        issue="CSV_UOM_MISMATCH",
                        sql_value=sql_row.value,
                        sql_uom=sql_row.uom,
                        csv_value=csv_val,
                        csv_uom=csv_uom,
                    ))

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
    sql_index: Dict[Tuple[str, str], SqlRow],
    summary: AuditSummary,
) -> None:
    """Detect properties in the wrong CSV file or absent from sql_index entirely."""
    sql_tag_set = {k[0] for k in sql_index}

    for _, row in df010.iterrows():
        tag  = _norm_prop_name(row.get("TAG_NAME", ""))
        prop = _norm_prop_name(row.get("PROPERTY_NAME", ""))
        if not tag or not prop:
            continue
        sql_row = sql_index.get((tag, prop))
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
        elif sql_row.concept == "Physical":
            summary.wrong_file_010.append(CsvGap(
                tag_name=row.get("TAG_NAME", ""),
                property_name=row.get("PROPERTY_NAME", ""),
                concept=sql_row.concept,
                layer="010",
                issue="CSV_WRONG_FILE",
                sql_value=sql_row.value,
                sql_uom=sql_row.uom,
                csv_value=row.get("PROPERTY_VALUE", ""),
                csv_uom=row.get("PROPERTY_VALUE_UOM", ""),
            ))

    for _, row in df011.iterrows():
        equip   = row.get("EQUIPMENT_NUMBER", "")
        tag_raw = equip[len(EQUIP_NUMBER_PREFIX):] if equip.upper().startswith(EQUIP_NUMBER_PREFIX.upper()) else equip
        tag  = _norm_prop_name(tag_raw)
        prop = _norm_prop_name(row.get("PROPERTY_NAME", ""))
        if not tag or not prop:
            continue
        sql_row = sql_index.get((tag, prop))
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
        elif sql_row.concept == "Functional":
            summary.wrong_file_011.append(CsvGap(
                tag_name=tag_raw,
                property_name=row.get("PROPERTY_NAME", ""),
                concept=sql_row.concept,
                layer="011",
                issue="CSV_WRONG_FILE",
                sql_value=sql_row.value,
                sql_uom=sql_row.uom,
                csv_value=row.get("PROPERTY_VALUE", ""),
                csv_uom=row.get("PROPERTY_VALUE_UOM", ""),
            ))


# ---------------------------------------------------------------------------
# Structural checks (duplicates, empty names) — unchanged logic
# ---------------------------------------------------------------------------

def _check_structural(
    df010: pd.DataFrame,
    df011: pd.DataFrame,
    summary: AuditSummary,
) -> None:
    """Check for duplicates and empty property names in export files."""
    if "TAG_NAME" in df010.columns and "PROPERTY_NAME" in df010.columns:
        dup010 = df010.duplicated(subset=["TAG_NAME", "PROPERTY_NAME"], keep=False)
        summary.duplicates_010 = int(dup010.sum())
        summary.empty_property_names_010 = int((df010["PROPERTY_NAME"].str.strip() == "").sum())

    if "EQUIPMENT_NUMBER" in df011.columns and "PROPERTY_NAME" in df011.columns:
        dup011 = df011.duplicated(subset=["EQUIPMENT_NUMBER", "PROPERTY_NAME"], keep=False)
        summary.duplicates_011 = int(dup011.sum())
        summary.empty_property_names_011 = int((df011["PROPERTY_NAME"].str.strip() == "").sum())


# ---------------------------------------------------------------------------
# Markdown rendering helpers
# ---------------------------------------------------------------------------

def _escape(s: str, max_len: int = 120) -> str:
    """Escape pipe chars and truncate for Markdown table cell."""
    s = str(s).replace("|", "｜")
    return s[:max_len] + "…" if len(s) > max_len else s


def _issue_icon(issue: str) -> str:
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
    n_sql_extra      = sum(1 for g in summary.rdl_sql_gaps if g.issue == "SQL_EXTRA")
    n_csv_miss_010   = sum(1 for g in summary.csv_gaps_010 if g.issue == "CSV_MISSING")
    n_csv_miss_011   = sum(1 for g in summary.csv_gaps_011 if g.issue == "CSV_MISSING")
    n_csv_mm_010     = sum(1 for g in summary.csv_gaps_010 if g.issue == "CSV_VALUE_MISMATCH")
    n_csv_mm_011     = sum(1 for g in summary.csv_gaps_011 if g.issue == "CSV_VALUE_MISMATCH")
    n_csv_uom_010    = sum(1 for g in summary.csv_gaps_010 if g.issue == "CSV_UOM_MISMATCH")
    n_csv_uom_011    = sum(1 for g in summary.csv_gaps_011 if g.issue == "CSV_UOM_MISMATCH")
    n_csv_na_010     = sum(1 for g in summary.csv_gaps_010 if g.issue == "CSV_NA_BLANK")
    n_csv_na_011     = sum(1 for g in summary.csv_gaps_011 if g.issue == "CSV_NA_BLANK")
    n_dup_010        = sum(1 for g in summary.csv_gaps_010 if "DUPLICATE" in g.issue)
    n_dup_011        = sum(1 for g in summary.csv_gaps_011 if "DUPLICATE" in g.issue)
    n_rdl_ref        = summary.total_rdl_tag_props + summary.total_rdl_equip_props - summary.total_rdl_both_props

    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| Metric | LAYER 1 (RDL vs SQL) | LAYER 2 (SQL vs CSV 010) | LAYER 2 (SQL vs CSV 011) |")
    lines.append("|--------|---------------------|--------------------------|--------------------------|")
    lines.append(f"| Reference rows | {n_rdl_ref:,} | {summary.sql_l2_tag_count:,} | {summary.sql_l2_equip_count:,} |")
    lines.append(f"| ⛔ SQL_MISSING (critical) | **{n_sql_missing:,}** | — | — |")
    lines.append(f"| ⚠️ SQL_VALUE_MISMATCH | {n_sql_mismatch:,} | — | — |")
    lines.append(f"| 📐 SQL_UOM_MISMATCH | {n_sql_uom:,} | — | — |")
    lines.append(f"| 🔕 SQL_NA_BLANK | {n_sql_na:,} | — | — |")
    lines.append(f"| ➕ SQL_EXTRA | {n_sql_extra:,} | — | — |")
    lines.append(f"| ❌ CSV_MISSING | — | **{n_csv_miss_010:,}** | **{n_csv_miss_011:,}** |")
    lines.append(f"| ⚠️ CSV_VALUE_MISMATCH | — | {n_csv_mm_010:,} | {n_csv_mm_011:,} |")
    lines.append(f"| 📐 CSV_UOM_MISMATCH | — | {n_csv_uom_010:,} | {n_csv_uom_011:,} |")
    lines.append(f"| 🔕 CSV_NA_BLANK | — | {n_csv_na_010:,} | {n_csv_na_011:,} |")
    lines.append(f"| 🔁 DUPLICATE | — | {n_dup_010:,} | {n_dup_011:,} |")
    lines.append(f"| 🔀 WRONG_FILE | — | {len(summary.wrong_file_010):,} | {len(summary.wrong_file_011):,} |")
    lines.append(f"| ➕ EXTRA (unknown) | — | {len(summary.extra_in_010):,} | {len(summary.extra_in_011):,} |")
    lines.append("")

    if n_sql_missing > 0:
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

    # Structural checks
    lines.append("### Structural Checks")
    lines.append("")
    lines.append(f"- {'🔁' if summary.duplicates_010 > 0 else '✅'} File 010 duplicate rows (TAG_NAME + PROPERTY_NAME): **{summary.duplicates_010}**")
    lines.append(f"- {'🔁' if summary.duplicates_011 > 0 else '✅'} File 011 duplicate rows (EQUIPMENT_NUMBER + PROPERTY_NAME): **{summary.duplicates_011}**")
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
            ("SQL_MISSING",       "⛔ SQL_MISSING — Critical: in RDL, absent from database"),
            ("SQL_VALUE_MISMATCH","⚠️ SQL_VALUE_MISMATCH"),
            ("SQL_UOM_MISMATCH",  "📐 SQL_UOM_MISMATCH"),
            ("SQL_NA_BLANK",      "🔕 SQL_NA_BLANK"),
            ("SQL_EXTRA",         "➕ SQL_EXTRA — In SQL but not in RDL"),
        ]:
            subset = [g for g in summary.rdl_sql_gaps if g.issue == issue_type]
            if not subset:
                continue
            lines.append(f"### {header} ({len(subset):,})")
            lines.append("")
            lines.extend(_render_rdl_sql_gap_table(subset))
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
            ("CSV_MISSING",       "❌ CSV_MISSING — In SQL, absent from export"),
            ("CSV_VALUE_MISMATCH","⚠️ CSV_VALUE_MISMATCH"),
            ("CSV_UOM_MISMATCH",  "📐 CSV_UOM_MISMATCH"),
            ("CSV_NA_BLANK",      "🔕 CSV_NA_BLANK"),
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
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

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

    print("Loading files...", end=" ", flush=True)
    rdl_raw = pd.read_excel(rdl_path, dtype=str).fillna("")
    rdl_raw.columns = rdl_raw.columns.str.strip()
    rdl   = _load_rdl(rdl_path)
    df010 = _load_csv(csv010_path)
    df011 = _load_csv(csv011_path)
    print(
        f"RDL rows={len(rdl):,} (pre-filter={len(rdl_raw):,})  "
        f"file010 rows={len(df010):,}  file011 rows={len(df011):,}"
    )

    summary = AuditSummary()
    summary.rdl_row_count_pre_filter = len(rdl_raw)

    # Layer 1 — load SQL data
    print("Querying DB...", end=" ", flush=True)
    sql_index = _load_sql_data(summary, no_db=args.no_db)
    if summary.sql_unavailable:
        print(f"unavailable ({summary.sql_error_msg[:80]})")
    else:
        print(f"done. sql_index={len(sql_index):,} entries  total_active={summary.sql_total_rows:,}")

    print("LAYER 1 — RDL vs SQL...", end=" ", flush=True)
    _detect_rdl_sql_gaps(rdl, sql_index, summary)
    n_l1_missing  = sum(1 for g in summary.rdl_sql_gaps if g.issue == "SQL_MISSING")
    n_l1_mismatch = sum(1 for g in summary.rdl_sql_gaps if g.issue == "SQL_VALUE_MISMATCH")
    print(f"done. SQL_MISSING={n_l1_missing:,}  SQL_MISMATCH={n_l1_mismatch:,}")

    print("Building CSV lookups...", end=" ", flush=True)
    lookup_010 = _build_export_lookup_010(df010)
    lookup_011 = _build_export_lookup_011(df011)
    print(f"010 keys={len(lookup_010):,}  011 keys={len(lookup_011):,}")

    print("LAYER 2 — SQL vs CSV...", end=" ", flush=True)
    _detect_sql_csv_gaps(sql_index, lookup_010, lookup_011, summary)
    n_l2_miss_010 = sum(1 for g in summary.csv_gaps_010 if g.issue == "CSV_MISSING")
    n_l2_miss_011 = sum(1 for g in summary.csv_gaps_011 if g.issue == "CSV_MISSING")
    print(f"done. CSV_MISSING_010={n_l2_miss_010:,}  CSV_MISSING_011={n_l2_miss_011:,}")

    print("Detecting wrong-file and extra...", end=" ", flush=True)
    _detect_wrong_and_extra(df010, df011, sql_index, summary)
    print(
        f"done. WRONG_010={len(summary.wrong_file_010):,}  WRONG_011={len(summary.wrong_file_011):,}  "
        f"EXTRA_010={len(summary.extra_in_010):,}  EXTRA_011={len(summary.extra_in_011):,}"
    )

    _check_structural(df010, df011, summary)

    total_gaps = (
        len(summary.rdl_sql_gaps)
        + len(summary.csv_gaps_010) + len(summary.csv_gaps_011)
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
