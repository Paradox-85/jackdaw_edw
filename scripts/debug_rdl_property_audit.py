"""
EIS Property Values RDL Audit Tool
====================================
Compares actual EIS CSV export files (file 010 and 011) against the master
RDL reference file (TagProperties-rdl.xlsx).

Routing logic (column: RDL Property Concept):
  - "Functional"          → must appear in file-010 (PLANT_CODE, TAG_NAME, PROPERTY_NAME, ...)
  - "Physical"            → must appear in file-011 (PLANT_CODE, EQUIPMENT_NUMBER, PROPERTY_NAME, ...)
  - "Functional Physical" → must appear in BOTH file-010 AND file-011
  - "Common"              → not validated (metadata properties, excluded)

Gap categories in output:
  [TAG-GAP]   Property expected in 010 (Functional / Functional Physical) but missing or wrong
  [EQUIP-GAP] Property expected in 011 (Physical / Functional Physical) but missing or wrong

Dev usage (F5 in VS Code — no args needed):
    Edit DEV_* paths below, then run.

CLI usage:
    python scripts/debug_rdl_property_audit.py \
        --rdl     "path/to/TagProperties-rdl.xlsx" \
        --file010 "path/to/JDAW-KVE-E-JA-6944-00001-010-A38.CSV" \
        --file011 "path/to/JDAW-KVE-E-JA-6944-00001-011-A38.CSV" \
        --output  "rdl_property_audit.md"

Output:
    Markdown report with full gap list and executive summary.
    Exit code 0 always (audit tool, not a CI blocker).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


# ---------------------------------------------------------------------------
# Dev defaults — edit these when running locally
# CLI args override these values
# ---------------------------------------------------------------------------

DEV_RDL_PATH   = Path(r"C:\path\to\TagProperties-rdl.xlsx")
DEV_FILE010    = Path(r"C:\path\to\JDAW-KVE-E-JA-6944-00001-010-A38.CSV")
DEV_FILE011    = Path(r"C:\path\to\JDAW-KVE-E-JA-6944-00001-011-A38.CSV")
DEV_OUTPUT     = Path(__file__).parent / "rdl_property_audit.md"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# RDL concepts that must appear in file 010 (TAG property values)
TAG_CONCEPTS = {"Functional", "Functional Physical"}

# RDL concepts that must appear in file 011 (EQUIPMENT property values)
EQUIP_CONCEPTS = {"Physical", "Functional Physical"}

# Concepts to skip entirely (metadata, not exported as property values)
SKIP_CONCEPTS = {"Common", ""}

# RDL column names
COL_TAG_NAME      = "Tag Name"
COL_RDL_PROP_NAME = "RDL Property Name"
COL_RDL_CONCEPT   = "RDL Property Concept"
COL_PROP_VALUE    = "Property Value"
COL_PROP_UOM      = "Property UoM"

# Equipment number prefix used in file-011 (e.g. "Equip_JDA-01MOV-03001")
EQUIP_NUMBER_PREFIX = "Equip_"

# Gap severity thresholds
WARN_GAP_PCT = 10.0


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PropertyGap:
    gap_type: str          # "TAG-GAP" | "EQUIP-GAP"
    tag_name: str
    property_name: str
    concept: str
    rdl_value: str
    rdl_uom: str
    export_value: str      # "" if missing entirely
    export_uom: str        # "" if missing entirely
    issue: str             # MISSING | VALUE_MISMATCH | UOM_MISMATCH | DUPLICATE | NA_EXPORTED_BLANK


@dataclass
class AuditSummary:
    total_rdl_tag_props: int = 0
    total_rdl_equip_props: int = 0
    total_rdl_both_props: int = 0
    tags_in_rdl: int = 0
    tags_in_010: int = 0
    tags_in_011_as_equip: int = 0

    tag_gaps: List[PropertyGap] = field(default_factory=list)
    equip_gaps: List[PropertyGap] = field(default_factory=list)

    # Structural checks
    duplicates_010: int = 0
    duplicates_011: int = 0
    empty_property_names_010: int = 0
    empty_property_names_011: int = 0

    # Tags present in RDL but fully absent from export
    tags_missing_from_010: List[str] = field(default_factory=list)
    tags_missing_from_011: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def _load_rdl(path: Path) -> pd.DataFrame:
    """Load TagProperties-rdl.xlsx, normalize column names."""
    df = pd.read_excel(path, dtype=str)
    df = df.fillna("")
    df.columns = df.columns.str.strip()
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
# Core audit logic
# ---------------------------------------------------------------------------

def _build_export_lookup_010(
    df: pd.DataFrame,
) -> Dict[Tuple[str, str], List[Tuple[str, str]]]:
    """
    Build lookup: (TAG_NAME_upper, PROPERTY_NAME_upper) -> [(value, uom), ...]
    Allows detection of duplicates (multiple rows for same key).
    """
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
    """
    Build lookup: (EQUIPMENT_NUMBER_upper, PROPERTY_NAME_upper) -> [(value, uom), ...]
    """
    lookup: Dict[Tuple[str, str], List[Tuple[str, str]]] = {}
    for _, row in df.iterrows():
        key = (_norm_prop_name(row.get("EQUIPMENT_NUMBER", "")),
               _norm_prop_name(row.get("PROPERTY_NAME", "")))
        val = (_norm_value(row.get("PROPERTY_VALUE", "")),
               _norm_value(row.get("PROPERTY_VALUE_UOM", "")))
        lookup.setdefault(key, []).append(val)
    return lookup


def _detect_gaps(
    rdl: pd.DataFrame,
    lookup_010: Dict,
    lookup_011: Dict,
    summary: AuditSummary,
) -> None:
    """
    Iterate every row in RDL, determine expected file(s), check export lookup.
    Populate summary.tag_gaps and summary.equip_gaps with full detail.
    """
    tags_needing_010: set = set()
    tags_needing_011: set = set()

    for _, row in rdl.iterrows():
        tag_name  = row.get(COL_TAG_NAME, "").strip()
        prop_name = row.get(COL_RDL_PROP_NAME, "").strip()
        concept   = row.get(COL_RDL_CONCEPT, "").strip()
        rdl_val   = row.get(COL_PROP_VALUE, "").strip()
        rdl_uom   = row.get(COL_PROP_UOM, "").strip()

        if not tag_name or not prop_name:
            continue
        if concept in SKIP_CONCEPTS:
            continue

        tag_key   = _norm_prop_name(tag_name)
        prop_key  = _norm_prop_name(prop_name)
        equip_key = _norm_prop_name(_equip_number(tag_name))

        # ----- FILE 010 CHECK (Functional + Functional Physical) -----
        if concept in TAG_CONCEPTS:
            tags_needing_010.add(tag_key)
            summary.total_rdl_tag_props += 1
            hits = lookup_010.get((tag_key, prop_key))

            if hits is None:
                summary.tag_gaps.append(PropertyGap(
                    gap_type="TAG-GAP",
                    tag_name=tag_name,
                    property_name=prop_name,
                    concept=concept,
                    rdl_value=rdl_val,
                    rdl_uom=rdl_uom,
                    export_value="",
                    export_uom="",
                    issue="MISSING",
                ))
            else:
                if len(hits) > 1:
                    summary.tag_gaps.append(PropertyGap(
                        gap_type="TAG-GAP",
                        tag_name=tag_name,
                        property_name=prop_name,
                        concept=concept,
                        rdl_value=rdl_val,
                        rdl_uom=rdl_uom,
                        export_value=hits[0][0],
                        export_uom=hits[0][1],
                        issue=f"DUPLICATE ({len(hits)} rows)",
                    ))

                if rdl_val.upper() == "NA" and hits[0][0] == "":
                    summary.tag_gaps.append(PropertyGap(
                        gap_type="TAG-GAP",
                        tag_name=tag_name,
                        property_name=prop_name,
                        concept=concept,
                        rdl_value=rdl_val,
                        rdl_uom=rdl_uom,
                        export_value=hits[0][0],
                        export_uom=hits[0][1],
                        issue="NA_EXPORTED_BLANK",
                    ))
                elif rdl_val and hits[0][0] and hits[0][0].upper() != rdl_val.upper():
                    summary.tag_gaps.append(PropertyGap(
                        gap_type="TAG-GAP",
                        tag_name=tag_name,
                        property_name=prop_name,
                        concept=concept,
                        rdl_value=rdl_val,
                        rdl_uom=rdl_uom,
                        export_value=hits[0][0],
                        export_uom=hits[0][1],
                        issue="VALUE_MISMATCH",
                    ))
                elif rdl_uom and hits[0][1] and hits[0][1].lower() != rdl_uom.lower():
                    summary.tag_gaps.append(PropertyGap(
                        gap_type="TAG-GAP",
                        tag_name=tag_name,
                        property_name=prop_name,
                        concept=concept,
                        rdl_value=rdl_val,
                        rdl_uom=rdl_uom,
                        export_value=hits[0][0],
                        export_uom=hits[0][1],
                        issue="UOM_MISMATCH",
                    ))

        # ----- FILE 011 CHECK (Physical + Functional Physical) -----
        if concept in EQUIP_CONCEPTS:
            tags_needing_011.add(equip_key)
            summary.total_rdl_equip_props += 1
            hits = lookup_011.get((equip_key, prop_key))

            if hits is None:
                summary.equip_gaps.append(PropertyGap(
                    gap_type="EQUIP-GAP",
                    tag_name=tag_name,
                    property_name=prop_name,
                    concept=concept,
                    rdl_value=rdl_val,
                    rdl_uom=rdl_uom,
                    export_value="",
                    export_uom="",
                    issue="MISSING",
                ))
            else:
                if len(hits) > 1:
                    summary.equip_gaps.append(PropertyGap(
                        gap_type="EQUIP-GAP",
                        tag_name=tag_name,
                        property_name=prop_name,
                        concept=concept,
                        rdl_value=rdl_val,
                        rdl_uom=rdl_uom,
                        export_value=hits[0][0],
                        export_uom=hits[0][1],
                        issue=f"DUPLICATE ({len(hits)} rows)",
                    ))
                elif rdl_val.upper() == "NA" and hits[0][0] == "":
                    summary.equip_gaps.append(PropertyGap(
                        gap_type="EQUIP-GAP",
                        tag_name=tag_name,
                        property_name=prop_name,
                        concept=concept,
                        rdl_value=rdl_val,
                        rdl_uom=rdl_uom,
                        export_value=hits[0][0],
                        export_uom=hits[0][1],
                        issue="NA_EXPORTED_BLANK",
                    ))
                elif rdl_val and hits[0][0] and hits[0][0].upper() != rdl_val.upper():
                    summary.equip_gaps.append(PropertyGap(
                        gap_type="EQUIP-GAP",
                        tag_name=tag_name,
                        property_name=prop_name,
                        concept=concept,
                        rdl_value=rdl_val,
                        rdl_uom=rdl_uom,
                        export_value=hits[0][0],
                        export_uom=hits[0][1],
                        issue="VALUE_MISMATCH",
                    ))
                elif rdl_uom and hits[0][1] and hits[0][1].lower() != rdl_uom.lower():
                    summary.equip_gaps.append(PropertyGap(
                        gap_type="EQUIP-GAP",
                        tag_name=tag_name,
                        property_name=prop_name,
                        concept=concept,
                        rdl_value=rdl_val,
                        rdl_uom=rdl_uom,
                        export_value=hits[0][0],
                        export_uom=hits[0][1],
                        issue="UOM_MISMATCH",
                    ))

    # Both-file props count
    summary.total_rdl_both_props = sum(
        1 for _, row in rdl.iterrows()
        if row.get(COL_RDL_CONCEPT, "").strip() == "Functional Physical"
    )

    # Tags missing entirely from exports
    tags_found_010 = {k[0] for k in lookup_010.keys()}
    summary.tags_missing_from_010 = sorted([
        t for t in tags_needing_010 if t not in tags_found_010
    ])

    tags_found_011 = {k[0] for k in lookup_011.keys()}
    summary.tags_missing_from_011 = sorted([
        t for t in tags_needing_011 if t not in tags_found_011
    ])


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

    summary.tags_in_010 = df010["TAG_NAME"].nunique() if "TAG_NAME" in df010.columns else 0
    summary.tags_in_011_as_equip = (
        df011["EQUIPMENT_NUMBER"].nunique()
        if "EQUIPMENT_NUMBER" in df011.columns else 0
    )


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def _escape(s: str, max_len: int = 120) -> str:
    """Escape pipe chars and truncate for Markdown table cell."""
    s = str(s).replace("|", "｜")
    return s[:max_len] + "…" if len(s) > max_len else s


def _issue_icon(issue: str) -> str:
    if "MISSING" in issue:
        return "❌"
    if "DUPLICATE" in issue:
        return "🔁"
    if "VALUE_MISMATCH" in issue:
        return "⚠️"
    if "UOM_MISMATCH" in issue:
        return "📐"
    if "NA_EXPORTED_BLANK" in issue:
        return "🔕"
    return "ℹ️"


def _render_gap_table(gaps: List[PropertyGap]) -> List[str]:
    lines = []
    lines.append(
        "| # | Icon | Tag Name | Property Name | Concept | Issue | "
        "RDL Value | RDL UoM | Export Value | Export UoM |"
    )
    lines.append(
        "|---|------|----------|---------------|---------|-------|"
        "-----------|---------|--------------|------------|"
    )
    for i, g in enumerate(gaps, start=1):
        lines.append(
            f"| {i} | {_issue_icon(g.issue)} | `{_escape(g.tag_name)}` "
            f"| `{_escape(g.property_name)}` | {g.concept} | **{g.issue}** "
            f"| {_escape(g.rdl_value)} | {_escape(g.rdl_uom)} "
            f"| {_escape(g.export_value)} | {_escape(g.export_uom)} |"
        )
    return lines


def render_report(
    summary: AuditSummary,
    rdl_path: Path,
    file010_path: Path,
    file011_path: Path,
) -> str:
    lines: List[str] = []

    lines.append("# EIS Property Values RDL Audit Report")
    lines.append("")
    lines.append(f"**RDL Reference:** `{rdl_path}`  ")
    lines.append(f"**File 010 (Tag Property Values):** `{file010_path}`  ")
    lines.append(f"**File 011 (Equipment Property Values):** `{file011_path}`  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    total_gaps = len(summary.tag_gaps) + len(summary.equip_gaps)
    missing_tag    = sum(1 for g in summary.tag_gaps   if g.issue == "MISSING")
    missing_equip  = sum(1 for g in summary.equip_gaps if g.issue == "MISSING")
    dup_tag        = sum(1 for g in summary.tag_gaps   if "DUPLICATE" in g.issue)
    dup_equip      = sum(1 for g in summary.equip_gaps if "DUPLICATE" in g.issue)
    na_blank_tag   = sum(1 for g in summary.tag_gaps   if g.issue == "NA_EXPORTED_BLANK")
    na_blank_equip = sum(1 for g in summary.equip_gaps if g.issue == "NA_EXPORTED_BLANK")

    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| Metric | File 010 (Tag) | File 011 (Equip) |")
    lines.append("|--------|---------------:|----------------:|")
    lines.append(f"| RDL properties expected | {summary.total_rdl_tag_props:,} | {summary.total_rdl_equip_props:,} |")
    lines.append(f"| Tags found in export | {summary.tags_in_010:,} | {summary.tags_in_011_as_equip:,} |")
    lines.append(f"| Tags missing from export entirely | {len(summary.tags_missing_from_010):,} | {len(summary.tags_missing_from_011):,} |")
    lines.append(f"| **Total gaps** | **{len(summary.tag_gaps):,}** | **{len(summary.equip_gaps):,}** |")
    lines.append(f"| ❌ MISSING | {missing_tag:,} | {missing_equip:,} |")
    lines.append(f"| ⚠️ VALUE_MISMATCH | {sum(1 for g in summary.tag_gaps if g.issue == 'VALUE_MISMATCH'):,} | {sum(1 for g in summary.equip_gaps if g.issue == 'VALUE_MISMATCH'):,} |")
    lines.append(f"| 📐 UOM_MISMATCH | {sum(1 for g in summary.tag_gaps if g.issue == 'UOM_MISMATCH'):,} | {sum(1 for g in summary.equip_gaps if g.issue == 'UOM_MISMATCH'):,} |")
    lines.append(f"| 🔁 DUPLICATE rows | {dup_tag:,} | {dup_equip:,} |")
    lines.append(f"| 🔕 NA exported as blank | {na_blank_tag:,} | {na_blank_equip:,} |")
    lines.append("")

    lines.append("### Structural Checks")
    lines.append("")
    lines.append(f"- {'🔁' if summary.duplicates_010 > 0 else '✅'} File 010 duplicate rows (TAG_NAME + PROPERTY_NAME): **{summary.duplicates_010}**")
    lines.append(f"- {'🔁' if summary.duplicates_011 > 0 else '✅'} File 011 duplicate rows (EQUIPMENT_NUMBER + PROPERTY_NAME): **{summary.duplicates_011}**")
    lines.append(f"- {'⚠️' if summary.empty_property_names_010 > 0 else '✅'} File 010 rows with empty PROPERTY_NAME: **{summary.empty_property_names_010}**")
    lines.append(f"- {'⚠️' if summary.empty_property_names_011 > 0 else '✅'} File 011 rows with empty PROPERTY_NAME: **{summary.empty_property_names_011}**")
    lines.append("")

    lines.append("### RDL Concept Routing Rules Applied")
    lines.append("")
    lines.append("| RDL Property Concept | Expected in 010 | Expected in 011 |")
    lines.append("|----------------------|:---------------:|:---------------:|")
    lines.append("| Functional           | ✅               | ❌               |")
    lines.append("| Physical             | ❌               | ✅               |")
    lines.append("| Functional Physical  | ✅               | ✅               |")
    lines.append("| Common               | — (skipped)     | — (skipped)     |")
    lines.append("")
    lines.append(f"> Note: `Functional Physical` properties counted as **{summary.total_rdl_both_props:,}** rows — each must appear in BOTH files.")
    lines.append("")
    lines.append("---")
    lines.append("")

    if summary.tags_missing_from_010:
        lines.append("### Tags Missing Entirely from File 010")
        lines.append("")
        lines.append("> These tags have Functional or Functional Physical properties in RDL but zero rows in file 010.")
        lines.append("")
        for t in summary.tags_missing_from_010:
            lines.append(f"- `{t}`")
        lines.append("")

    if summary.tags_missing_from_011:
        lines.append("### Tags Missing Entirely from File 011")
        lines.append("")
        lines.append("> These tags have Physical or Functional Physical properties in RDL but zero rows in file 011.")
        lines.append("")
        for t in summary.tags_missing_from_011:
            lines.append(f"- `{t}`")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Full gap tables — file 010
    lines.append("## TAG-GAP — File 010 (Tag Property Values) Full Gap List")
    lines.append("")
    lines.append("> All rows where a property expected in file 010 is missing, mismatched, duplicated, or NA exported as blank.")
    lines.append("")

    if summary.tag_gaps:
        issue_order = ["MISSING", "VALUE_MISMATCH", "UOM_MISMATCH", "NA_EXPORTED_BLANK"]
        for issue_type in issue_order:
            subset = [g for g in summary.tag_gaps if g.issue == issue_type]
            if not subset:
                continue
            lines.append(f"### {_issue_icon(issue_type)} {issue_type} — {len(subset):,} gap(s) in file 010")
            lines.append("")
            lines.extend(_render_gap_table(subset))
            lines.append("")
        dup_subset = [g for g in summary.tag_gaps if "DUPLICATE" in g.issue]
        if dup_subset:
            lines.append(f"### 🔁 DUPLICATE — {len(dup_subset):,} gap(s) in file 010")
            lines.append("")
            lines.extend(_render_gap_table(dup_subset))
            lines.append("")
    else:
        lines.append("✅ No TAG-GAP issues found in file 010.")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Full gap tables — file 011
    lines.append("## EQUIP-GAP — File 011 (Equipment Property Values) Full Gap List")
    lines.append("")
    lines.append("> All rows where a property expected in file 011 is missing, mismatched, duplicated, or NA exported as blank.")
    lines.append("")

    if summary.equip_gaps:
        issue_order = ["MISSING", "VALUE_MISMATCH", "UOM_MISMATCH", "NA_EXPORTED_BLANK"]
        for issue_type in issue_order:
            subset = [g for g in summary.equip_gaps if g.issue == issue_type]
            if not subset:
                continue
            lines.append(f"### {_issue_icon(issue_type)} {issue_type} — {len(subset):,} gap(s) in file 011")
            lines.append("")
            lines.extend(_render_gap_table(subset))
            lines.append("")
        dup_subset = [g for g in summary.equip_gaps if "DUPLICATE" in g.issue]
        if dup_subset:
            lines.append(f"### 🔁 DUPLICATE — {len(dup_subset):,} gap(s) in file 011")
            lines.append("")
            lines.extend(_render_gap_table(dup_subset))
            lines.append("")
    else:
        lines.append("✅ No EQUIP-GAP issues found in file 011.")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Legend")
    lines.append("")
    lines.append("| Icon | Code | Meaning |")
    lines.append("|------|------|---------|")
    lines.append("| ❌ | MISSING | Property expected per RDL concept but has zero rows in export |")
    lines.append("| ⚠️ | VALUE_MISMATCH | Property found in export but value differs from RDL reference |")
    lines.append("| 📐 | UOM_MISMATCH | Property found but unit of measure differs from RDL reference |")
    lines.append("| 🔁 | DUPLICATE | Same TAG_NAME + PROPERTY_NAME appears more than once in export |")
    lines.append("| 🔕 | NA_EXPORTED_BLANK | RDL has 'NA' but export has empty string (ETL NA-blanking bug) |")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Audit EIS property value export files against RDL master.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--rdl",     default=None, metavar="FILE",
                   help="Path to TagProperties-rdl.xlsx")
    p.add_argument("--file010", default=None, metavar="FILE",
                   help="Path to JDAW-...-010-*.CSV")
    p.add_argument("--file011", default=None, metavar="FILE",
                   help="Path to JDAW-...-011-*.CSV")
    p.add_argument("--output",  default=None, metavar="FILE",
                   help="Output .md report path (default: rdl_property_audit.md in scripts/)")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    rdl_path     = Path(args.rdl)     if args.rdl     else DEV_RDL_PATH
    file010_path = Path(args.file010) if args.file010 else DEV_FILE010
    file011_path = Path(args.file011) if args.file011 else DEV_FILE011
    output_path  = Path(args.output)  if args.output  else DEV_OUTPUT

    print(f"RDL reference:  {rdl_path}")
    print(f"File 010 (Tag): {file010_path}")
    print(f"File 011 (Eq):  {file011_path}")
    print(f"Output:         {output_path}")

    for p, label in [(rdl_path, "RDL"), (file010_path, "file010"), (file011_path, "file011")]:
        if not p.exists():
            print(f"ERROR: {label} file not found: {p}")
            return 1

    print("Loading files...", end=" ")
    rdl   = _load_rdl(rdl_path)
    df010 = _load_csv(file010_path)
    df011 = _load_csv(file011_path)
    print(f"RDL rows={len(rdl):,}  file010 rows={len(df010):,}  file011 rows={len(df011):,}")

    print("Building export lookups...", end=" ")
    lookup_010 = _build_export_lookup_010(df010)
    lookup_011 = _build_export_lookup_011(df011)
    print(f"010 unique keys={len(lookup_010):,}  011 unique keys={len(lookup_011):,}")

    print("Running audit...", end=" ")
    summary = AuditSummary()
    _detect_gaps(rdl, lookup_010, lookup_011, summary)
    _check_structural(df010, df011, summary)
    total_gaps = len(summary.tag_gaps) + len(summary.equip_gaps)
    print(f"done. Total gaps: {total_gaps:,} (TAG={len(summary.tag_gaps):,}, EQUIP={len(summary.equip_gaps):,})")

    md = render_report(summary, rdl_path, file010_path, file011_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")
    print(f"\nReport written to: {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
