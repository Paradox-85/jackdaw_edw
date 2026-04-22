#!/usr/bin/env python3
"""Diagnostic script: Debug tag comparison logic.

Shows field-by-field diff between current state and baseline snapshot
for a given tag, exposing the root cause of false "Modified" results.

Usage:
    python test/debug_tag_comparison.py --tag JDA-A-84001A
    python test/debug_tag_comparison.py --tag JDA-A-84001A --current-date 2026-04-20 --baseline-date 2026-03-09
"""

import argparse
import json
import sys
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from pathlib import Path
from sqlalchemy import create_engine, text
import pandas as pd

# ETL path setup: scripts/ is one level below repo root, etl/ is at repo root
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "etl"))

try:
    from tasks.common import load_config, get_db_engine_url
except ImportError as e:
    print(f"[ERROR] Could not import task modules. Details: {e}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# SQL queries
# ---------------------------------------------------------------------------

_SQL_MAX_CURRENT_DATE = """
SELECT MAX(sync_timestamp)::date AS max_date
FROM project_core.tag
WHERE object_status = 'Active'
"""

_SQL_NEAREST_BASELINE_DATE = """
SELECT MAX(sync_timestamp)::date AS nearest_date
FROM audit_core.tag_status_history
WHERE sync_timestamp::date <= :target_date
"""

_SQL_CURRENT_TAG = """
SELECT
    source_id, tag_name, tag_status, description, parent_tag_raw,
    tag_class_raw, area_code_raw, process_unit_raw, discipline_code_raw,
    po_code_raw, design_company_name_raw, manufacturer_company_raw,
    vendor_company_raw, article_code_raw, model_part_raw,
    safety_critical_item, safety_critical_item_reason_awarded,
    production_critical_item, safety_critical_item_group,
    serial_no, install_date, startup_date,
    warranty_end_date, price, tech_id, ip_grade, ex_class,
    mc_package_code, equip_no, alias, from_tag_raw, to_tag_raw,
    plant_raw, sync_status, object_status, row_hash, sync_timestamp
FROM project_core.tag
WHERE id = :tag_id
  AND object_status = 'Active'
  AND sync_timestamp::date <= :current_date
"""

_SQL_TAG_ID = """
SELECT id FROM project_core.tag WHERE tag_name = :tag_name
"""

_SQL_BASELINE_SNAPSHOT = """
SELECT DISTINCT ON (tag_id)
    tag_id, tag_name, row_hash, snapshot, sync_timestamp, sync_status
FROM audit_core.tag_status_history
WHERE tag_id = :tag_id
  AND sync_timestamp::date <= :baseline_date
ORDER BY tag_id, sync_timestamp DESC
"""

_SQL_PO_DATE = """
SELECT po_date::date AS purchase_date
FROM reference_core.purchase_order
WHERE name = :po_code
   OR code = :po_code
LIMIT 1
"""

# ---------------------------------------------------------------------------
# Mapping tables
# ---------------------------------------------------------------------------

SNAPSHOT_KEY_TO_COLUMN = {
    "tn": "tag_name",
    "t_stat": "tag_status",
    "cls_raw": "tag_class_raw",
    "art_raw": "article_code_raw",
    "dco_raw": "design_company_name_raw",
    "area_raw": "area_code_raw",
    "unit_raw": "process_unit_raw",
    "plt_raw": "plant_raw",
    "disc_raw": "discipline_code_raw",
    "po_raw": "po_code_raw",
    "sn": "serial_no",
    "tid": "tech_id",
    "als": "alias",
    "dsc": "description",
    "inst": "install_date",
    "start": "startup_date",
    "warn": "warranty_end_date",
    "prc": "price",
    "m_raw": "model_part_raw",
    "mfr_raw": "manufacturer_company_raw",
    "v_raw": "vendor_company_raw",
    "prnt_raw": "parent_tag_raw",
    "ex_cls": "ex_class",
    "ip_gr": "ip_grade",
    "mc_pkg": "mc_package_code",
    "from_tag_raw": "from_tag_raw",
    "to_tag_raw": "to_tag_raw",
    "sci": "safety_critical_item",
    "sci_rea": "safety_critical_item_reason_awarded",
    "pci": "production_critical_item",
    "sece_grp": "safety_critical_item_group",
    "eq": "equip_no",
}

EIS_FIELDS_TO_COLUMN = {
    "PLANT_CODE": "plant_raw",
    "TAG_NAME": "tag_name",
    "PARENT_TAG_NAME": "parent_tag_raw",
    "AREA_CODE": "area_code_raw",
    "PROCESS_UNIT_CODE": "process_unit_raw",
    "TAG_CLASS_NAME": "tag_class_raw",
    "TAG_STATUS": "tag_status",
    "REQUISITION_CODE": "po_code_raw",
    "DESIGNED_BY_COMPANY_NAME": "design_company_name_raw",
    "COMPANY_NAME": "design_company_name_raw",  # NOTE: maps to design_company_name_raw
    "PO_CODE": "po_code_raw",
    "PRODUCTION_CRITICAL_ITEM": "production_critical_item",
    "SAFETY_CRITICAL_ITEM": "safety_critical_item",
    "SAFETY_CRITICAL_ITEM_GROUP": "safety_critical_item_group",  # FIXED: now maps to DB column
    "SAFETY_CRITICAL_ITEM_REASON_AWARDED": "safety_critical_item_reason_awarded",
    "TAG_DESCRIPTION": "description",
    "EQUIPMENT_NUMBER": "equip_no",  # FIXED: now in snapshot
    "EQUIPMENT_CLASS_NAME": "tag_class_raw",
    "MANUFACTURER_COMPANY_NAME": "manufacturer_company_raw",
    "MODEL_PART_NAME": "model_part_raw",
    "MANUFACTURER_SERIAL_NUMBER": "serial_no",
    "PURCHASE_DATE": "__derived_po_date__",  # FIXED: derived from po_code_raw
    "VENDOR_COMPANY_NAME": "vendor_company_raw",
    "INSTALLATION_DATE": "install_date",
    "STARTUP_DATE": "startup_date",
    "PRICE": "price",
    "WARRANTY_END_DATE": "warranty_end_date",
    "PART_OF": "parent_tag_raw",
    "TECHIDENTNO": "tech_id",
    "ALIAS": "alias",
}

_DATE_COLS = {"install_date", "startup_date", "warranty_end_date"}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _to_str(value) -> str:
    """Convert any value to string; None/NaN/NaT map to empty string."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _normalize_value(value) -> str:
    """Normalize value for comparison: None→'', strip whitespace."""
    return _to_str(value).strip()


def _normalize_date(value) -> str:
    """Normalize date to YYYY-MM-DD string or empty string."""
    if value is None or value == "":
        return ""
    try:
        dt = pd.to_datetime(value, errors="coerce")
        if pd.isna(dt):
            return ""
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


def print_separator():
    """Print a visual separator line."""
    print("═" * 80)


def print_header(title: str):
    """Print a section header."""
    print()
    print(f"=== {title} ===")
    print()


# ---------------------------------------------------------------------------
# Main implementation
# ---------------------------------------------------------------------------


def main():
    """Main diagnostic routine."""
    parser = argparse.ArgumentParser(
        description="Диагностика сравнения тегов — показывает field-by-field diff"
    )
    parser.add_argument("--tag", required=True, help="TAG_NAME для диагностики")
    parser.add_argument(
        "--current-date",
        type=lambda s: date.fromisoformat(s),
        help="Дата в формате YYYY-MM-DD (по умолчанию: сегодня)"
    )
    parser.add_argument(
        "--baseline-date",
        type=lambda s: date.fromisoformat(s),
        help="Дата в формате YYYY-MM-DD (по умолчанию: ближайшая доступная ≤ current_date - 1 месяц)"
    )
    args = parser.parse_args()

    # Load config and DB engine
    config = load_config()
    db_url = get_db_engine_url(config)
    engine = create_engine(db_url)

    # STEP 1: Resolve dates
    print_header("STEP 1: RESOLVE DATES")

    current_date = args.current_date
    if current_date is None:
        with engine.connect() as conn:
            row = conn.execute(text(_SQL_MAX_CURRENT_DATE)).fetchone()
        if row is None or row[0] is None:
            print("[ERROR] project_core.tag contains no active records.")
            sys.exit(1)
        current_date = row[0]
        print(f"[INFO] current_date  : {current_date} (resolved from DB MAX)")
    else:
        print(f"[INFO] current_date  : {current_date} (from CLI)")

    baseline_date = args.baseline_date
    if baseline_date is None:
        target_date = current_date - relativedelta(months=1)
        with engine.connect() as conn:
            row = conn.execute(
                text(_SQL_NEAREST_BASELINE_DATE).bindparams(target_date=str(target_date))
            ).fetchone()
        if row is None or row[0] is None:
            print("[ERROR] No history records found.")
            sys.exit(1)
        baseline_date = row[0]
        print(
            f"[INFO] baseline_date : {baseline_date} (nearest to target {target_date})"
        )
    else:
        print(f"[INFO] baseline_date : {baseline_date} (from CLI)")

    # STEP 2: Resolve tag_id from tag_name (stable DB primary key)
    print_header("STEP 2: RESOLVE TAG_ID")

    with engine.connect() as conn:
        result = conn.execute(text(_SQL_TAG_ID).bindparams(tag_name=args.tag)).fetchone()

    if result is None:
        print(f"[ERROR] Tag '{args.tag}' not found in project_core.tag")
        sys.exit(1)

    tag_id = result[0]
    print(f"[INFO] Resolved tag_id: {tag_id} from tag_name: {args.tag}")

    # STEP 3: Load current state from project_core.tag using stable tag_id
    print_header("STEP 3: LOAD CURRENT STATE")

    with engine.connect() as conn:
        result = conn.execute(
            text(_SQL_CURRENT_TAG).bindparams(
                tag_id=tag_id, current_date=str(current_date)
            )
        ).fetchone()

    if result is None:
        print(f"[ERROR] Tag with id={tag_id} not found in project_core.tag")
        sys.exit(1)

    current_row = dict(result._mapping)
    print(f"[INFO] Loaded current state for tag_id: {tag_id}")
    for key, value in current_row.items():
        print(f"  {key:40} = {value!r}")

    # STEP 4: Load baseline snapshot from audit_core.tag_status_history
    print_header("STEP 4: LOAD BASELINE SNAPSHOT")

    # Load baseline snapshot
    with engine.connect() as conn:
        result = conn.execute(
            text(_SQL_BASELINE_SNAPSHOT).bindparams(
                tag_id=tag_id, baseline_date=str(baseline_date)
            )
        ).fetchone()

    if result is None:
        print(
            f"[WARNING] No baseline snapshot found for tag_id={tag_id} on or before {baseline_date}"
        )
        print("[INFO] All fields will appear as Created (no baseline)")
        baseline_snapshot = None
        baseline_row_hash = None
        baseline_sync_status = None
        baseline_timestamp = None
    else:
        baseline_row = dict(result._mapping)
        baseline_snapshot = baseline_row.get("snapshot")
        baseline_row_hash = baseline_row.get("row_hash")
        baseline_sync_status = baseline_row.get("sync_status")
        baseline_timestamp = baseline_row.get("sync_timestamp")

        print(
            f"[INFO] Baseline record found: sync_timestamp={baseline_timestamp}, "
            f"sync_status={baseline_sync_status}"
        )
        print(f"[INFO] row_hash (baseline): {baseline_row_hash}")
        print(f"[INFO] row_hash (current) : {current_row.get('row_hash')}")
        hashes_match = baseline_row_hash == current_row.get("row_hash")
        print(f"[INFO] Hashes match: {'YES' if hashes_match else 'NO'}")

        if isinstance(baseline_snapshot, dict):
            print(
                f"[DEBUG] Raw snapshot keys: {sorted(baseline_snapshot.keys())}"
            )
            print("[DEBUG] Raw snapshot content:")
            print(json.dumps(baseline_snapshot, indent=2))
        else:
            print(f"[DEBUG] Snapshot is not a dict: {type(baseline_snapshot)}")

    # STEP 4: Map snapshot keys to project_core.tag column names
    print_header("STEP 4: MAP SNAPSHOT KEYS")

    baseline_values = {}
    if baseline_snapshot:
        for snapshot_key, db_col in SNAPSHOT_KEY_TO_COLUMN.items():
            baseline_values[db_col] = baseline_snapshot.get(snapshot_key)

        print(f"[INFO] Snapshot contains {len(baseline_values)} fields after key mapping.")
        for db_col, value in sorted(baseline_values.items()):
            print(f"  {db_col:40} = {value!r}")
    else:
        print("[INFO] No snapshot to map (baseline not found)")

    # Check which fields are NOT in snapshot
    missing_in_snapshot = set()
    for eis_field, db_col in EIS_FIELDS_TO_COLUMN.items():
        if db_col and db_col not in baseline_values:
            missing_in_snapshot.add((eis_field, db_col))

    if missing_in_snapshot:
        print("[INFO] Fields NOT in snapshot (will appear as blank in comparison):")
        for eis_field, db_col in sorted(missing_in_snapshot):
            print(f"  {eis_field:30} → {db_col}")

    # STEP 5: Field-level diff
    print_header("STEP 5: FIELD-LEVEL COMPARISON")

    diff_results = []
    for eis_field, db_col in sorted(EIS_FIELDS_TO_COLUMN.items()):
        if db_col is None:
            # EIS field has no DB column
            diff_results.append(
                {
                    "EIS_FIELD": eis_field,
                    "VALUE_OLD": "<not mapped to DB column>",
                    "VALUE_NEW": "<not mapped to DB column>",
                    "RESULT": "⚠ NO DB COLUMN",
                }
            )
            continue

        # FIXED: Handle derived PURCHASE_DATE field
        if db_col == "__derived_po_date__":
            # Resolve purchase_date from po_code_raw via reference_core.purchase_order
            po_code_new = current_row.get("po_code_raw", "")
            po_code_old = baseline_snapshot.get("po_raw") if baseline_snapshot else ""

            val_new = ""
            if po_code_new:
                with engine.connect() as conn:
                    result = conn.execute(
                        text(_SQL_PO_DATE).bindparams(po_code=po_code_new)
                    ).fetchone()
                if result and result[0]:
                    val_new = str(result[0])

            val_old = ""
            if po_code_old:
                with engine.connect() as conn:
                    result = conn.execute(
                        text(_SQL_PO_DATE).bindparams(po_code=po_code_old)
                    ).fetchone()
                if result and result[0]:
                    val_old = str(result[0])

            if val_old != val_new:
                result = "✓ CHANGED"
                display_old = val_old
            else:
                result = "= SAME"
                display_old = val_old

            diff_results.append(
                {
                    "EIS_FIELD": eis_field,
                    "VALUE_OLD": display_old,
                    "VALUE_NEW": val_new,
                    "RESULT": result,
                }
            )
            continue

        # Regular DB columns
        val_old_raw = baseline_values.get(db_col, "")
        val_new_raw = current_row.get(db_col, "")

        # FIXED: Normalize val_old via _normalize_value() to strip whitespace and handle sentinels
        val_old = _normalize_value(val_old_raw)

        # Normalize dates
        if db_col in _DATE_COLS:
            val_old = _normalize_date(val_old)
            val_new = _normalize_date(val_new_raw)
        else:
            val_new = _normalize_value(val_new_raw)

        # Check if field is missing in snapshot
        if db_col not in baseline_values:
            result = "⚠ MISSING IN SNAPSHOT"
            display_old = "<empty — not in snapshot>"
        elif db_col in missing_in_snapshot:
            result = "⚠ MISSING IN SNAPSHOT"
            display_old = _to_str(val_old) if val_old else "<empty — not in snapshot>"
        elif val_old != val_new:
            result = "✓ CHANGED"
            display_old = _to_str(val_old)
        else:
            result = "= SAME"
            display_old = _to_str(val_old)

        diff_results.append(
            {
                "EIS_FIELD": eis_field,
                "VALUE_OLD": _to_str(display_old),
                "VALUE_NEW": _to_str(val_new),
                "RESULT": result,
            }
        )

    # STEP 6: Output results
    print_separator()
    print(f"COMPARISON RESULT for tag: {args.tag}")
    print(f"current_date: {current_date}  |  baseline_date: {baseline_date}")
    print_separator()
    print()

    # Print table header
    print(
        f"{'EIS_FIELD':30} | {'VALUE_OLD':30} | {'VALUE_NEW':30} | {'RESULT':20}"
    )
    print("-" * 100)

    # Print each row
    for row in diff_results:
        print(
            f"{row['EIS_FIELD']:30} | {str(row['VALUE_OLD'] or '')[:30]:30} | "
            f"{str(row['VALUE_NEW'] or '')[:30]:30} | {row['RESULT']:20}"
        )

    # Print summary
    print()
    print_separator()
    print("[SUMMARY]")

    total_checked = len(diff_results)
    changed = sum(1 for r in diff_results if r["RESULT"] == "✓ CHANGED")
    same = sum(1 for r in diff_results if r["RESULT"] == "= SAME")
    missing_in_snapshot_count = sum(
        1 for r in diff_results if r["RESULT"] == "⚠ MISSING IN SNAPSHOT"
    )
    no_db_column = sum(
        1 for r in diff_results if r["RESULT"] == "⚠ NO DB COLUMN"
    )

    print(f"Total EIS fields checked : {total_checked}")
    print(f"CHANGED                  : {changed}")
    print(f"SAME                     : {same}")
    print(f"MISSING IN SNAPSHOT      : {missing_in_snapshot_count}")
    print(f"NO DB COLUMN             : {no_db_column}")

    snapshot_covers_current = missing_in_snapshot_count == 0
    print(
        f"SNAPSHOT COVERS CURRENT  : {'YES' if snapshot_covers_current else 'NO'} "
        f"({'YES' if snapshot_covers_current else f'NO — {missing_in_snapshot_count} fields missing'})"
    )

    print()
    print("[EXPLANATION]")
    if missing_in_snapshot_count > 0:
        print(
            "⚠ Some fields are missing from the snapshot. This is the ROOT CAUSE of "
            "false 'Modified' results in export_tag_comparison_deploy.py."
        )
        print("  The snapshot stores values with SHORT keys (e.g., 't_stat'), but the "
              "comparison expects FULL column names (e.g., 'tag_status').")
        print("  Without the key mapping, baseline values default to empty strings '', "
              "causing false positives.")
    else:
        print("✓ Snapshot covers all fields. If 'Modified' results appear, they are "
              "genuine changes.")
    print()


if __name__ == "__main__":
    main()
