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
FROM audit_core.tag_status_history
"""

_SQL_NEAREST_BASELINE_DATE = """
SELECT MAX(sync_timestamp)::date AS nearest_date
FROM audit_core.tag_status_history
WHERE sync_timestamp::date <= :target_date
"""

_SQL_SNAPSHOT_FOR_DATE = """
/*
Purpose: Most recent per-tag snapshot on or before target_date.
Gate:    sync_timestamp::date <= target_date.
Note:    DISTINCT ON picks the latest history record per tag.
         Used for BOTH current and baseline states.
Changes: 2026-04-22 — Renamed from _SQL_BASELINE_SNAPSHOT, now used for both sides.
*/
SELECT DISTINCT ON (source_id)
    source_id,
    tag_name,
    row_hash,
    snapshot,
    sync_timestamp
FROM audit_core.tag_status_history
WHERE sync_timestamp::date <= :target_date
ORDER BY source_id, sync_timestamp DESC
"""

_SQL_SNAPSHOT_FOR_TAG = """
/*
Purpose: Most recent snapshot for a specific tag on or before target_date.
Gate:    sync_timestamp::date <= target_date, tag_name = :tag_name.
Note:    DISTINCT ON picks the latest history record for the specific tag.
         Used for debug script to isolate a single tag's state.
Changes: 2026-04-22 — Added for debug_tag_comparison.py snapshot filtering.
*/
SELECT DISTINCT ON (source_id)
    source_id,
    tag_name,
    row_hash,
    snapshot,
    sync_timestamp
FROM audit_core.tag_status_history
WHERE sync_timestamp::date <= :target_date
  AND tag_name = :tag_name
ORDER BY source_id, sync_timestamp DESC
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
    # ADD: 3 new mappings for Bug 1-2-3
    "purch_dt": "purchase_date",      # ADD: Bug 3
    "co_raw": "company_raw",          # ADD: Bug 1
    "part_of_raw": "part_of",         # ADD: Bug 2
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
    # FIX Bug 1: COMPANY_NAME should map to company_raw (not design_company_name_raw)
    "COMPANY_NAME": "company_raw",
    "PO_CODE": "po_code_raw",
    "PRODUCTION_CRITICAL_ITEM": "production_critical_item",
    "SAFETY_CRITICAL_ITEM": "safety_critical_item",
    "SAFETY_CRITICAL_ITEM_GROUP": "safety_critical_item_group",
    "SAFETY_CRITICAL_ITEM_REASON_AWARDED": "safety_critical_item_reason_awarded",
    "TAG_DESCRIPTION": "description",
    "EQUIPMENT_NUMBER": "equip_no",
    "EQUIPMENT_CLASS_NAME": "tag_class_raw",
    "MANUFACTURER_COMPANY_NAME": "manufacturer_company_raw",
    "MODEL_PART_NAME": "model_part_raw",
    "MANUFACTURER_SERIAL_NUMBER": "serial_no",
    # FIX Bug 3: PURCHASE_DATE should map to purchase_date (not derived field)
    "PURCHASE_DATE": "purchase_date",
    "VENDOR_COMPANY_NAME": "vendor_company_raw",
    "INSTALLATION_DATE": "install_date",
    "STARTUP_DATE": "startup_date",
    "PRICE": "price",
    "WARRANTY_END_DATE": "warranty_end_date",
    # FIX Bug 2: PART_OF should map to part_of (not parent_tag_raw)
    "PART_OF": "part_of",
    "TECHIDENTNO": "tech_id",
    "ALIAS": "alias",
}

_DATE_COLS = {"install_date", "startup_date", "warranty_end_date", "purchase_date"}  # ADD: purchase_date

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

    # STEP 2: Load current state from snapshot
    print_header("STEP 2: LOAD CURRENT SNAPSHOT")

    # Load current snapshot (same logic as baseline)
    with engine.connect() as conn:
        result = conn.execute(
            text(_SQL_SNAPSHOT_FOR_TAG).bindparams(
                target_date=str(current_date), tag_name=args.tag
            )
        ).fetchone()

    if result is None:
        print(f"[WARNING] No current snapshot found for source_id={args.tag} on or before {current_date}")
        print("[INFO] All fields will appear as Created (no current snapshot)")
        current_snapshot = None
        current_row_hash = None
        current_sync_status = None
        current_timestamp = None
    else:
        current_row = dict(result._mapping)
        current_snapshot = current_row.get("snapshot")
        current_row_hash = current_row.get("row_hash")
        current_sync_status = current_row.get("sync_status")
        current_timestamp = current_row.get("sync_timestamp")

        print(
            f"[INFO] Current snapshot found: sync_timestamp={current_timestamp}, "
            f"sync_status={current_sync_status}"
        )
        print(f"[INFO] row_hash (current): {current_row_hash}")

        if isinstance(current_snapshot, dict):
            print(
                f"[DEBUG] Raw snapshot keys: {sorted(current_snapshot.keys())}"
            )
            print("[DEBUG] Raw snapshot content:")
            print(json.dumps(current_snapshot, indent=2))
        else:
            print(f"[DEBUG] Snapshot is not a dict: {type(current_snapshot)}")

    # STEP 3: Map snapshot keys to project_core.tag column names
    print_header("STEP 3: MAP CURRENT SNAPSHOT KEYS")

    current_values = {}
    if current_snapshot:
        for snapshot_key, db_col in SNAPSHOT_KEY_TO_COLUMN.items():
            current_values[db_col] = current_snapshot.get(snapshot_key)

        print(f"[INFO] Current snapshot contains {len(current_values)} fields after key mapping.")
        for db_col, value in sorted(current_values.items()):
            print(f"  {db_col:40} = {value!r}")
    else:
        print("[INFO] No snapshot to map (current not found)")

    # STEP 4: Load baseline snapshot from audit_core.tag_status_history
    print_header("STEP 4: LOAD BASELINE SNAPSHOT")

    # Load baseline snapshot
    with engine.connect() as conn:
        result = conn.execute(
            text(_SQL_SNAPSHOT_FOR_TAG).bindparams(
                target_date=str(baseline_date), tag_name=args.tag
            )
        ).fetchone()

    if result is None:
        print(
            f"[WARNING] No baseline snapshot found for source_id={args.tag} on or before {baseline_date}"
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
        print(f"[INFO] row_hash (current) : {current_row_hash}")
        hashes_match = baseline_row_hash == current_row_hash
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
    print_header("STEP 5: MAP BASELINE SNAPSHOT KEYS")

    baseline_values = {}
    if baseline_snapshot:
        for snapshot_key, db_col in SNAPSHOT_KEY_TO_COLUMN.items():
            baseline_values[db_col] = baseline_snapshot.get(snapshot_key)

        print(f"[INFO] Baseline snapshot contains {len(baseline_values)} fields after key mapping.")
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
    print_header("STEP 6: FIELD-LEVEL COMPARISON")

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

        # Regular DB columns
        val_old_raw = baseline_values.get(db_col, "")
        val_new_raw = current_values.get(db_col, "")  # CHANGED: from current_row to current_values

        # Normalize val_old via _normalize_value() to strip whitespace and handle sentinels
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

    # STEP 7: Output results
    print_header("STEP 7: OUTPUT RESULTS")
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
