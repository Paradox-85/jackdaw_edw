"""One-time deduplication of project_core.property_value.

Identifies and removes duplicate rows where
(tag_id, property_id, property_value, property_uom_raw, object_status) are identical,
keeping the row with the lowest id.

Usage:
    python scripts/deduplicate_property_values.py          # dry-run (default, safe)
    python scripts/deduplicate_property_values.py --apply  # execute DELETE

Pre-condition: run --dry-run first and confirm rows_to_delete before --apply.
Note: As of 2026-05-07 duplicate_count = 0. Script is a safety check before
      adding the UNIQUE constraint (Fix E).
"""

import argparse
import os

from sqlalchemy import create_engine, text

_COUNT_SQL = """
WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY tag_id, property_id, property_value, property_uom_raw, object_status
            ORDER BY id ASC
        ) AS rn
    FROM project_core.property_value
    WHERE object_status = 'Active'
)
SELECT COUNT(*) FROM ranked WHERE rn > 1
"""

_DELETE_SQL = """
WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY tag_id, property_id, property_value, property_uom_raw, object_status
            ORDER BY id ASC
        ) AS rn
    FROM project_core.property_value
    WHERE object_status = 'Active'
)
DELETE FROM project_core.property_value
WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute DELETE (default: dry-run only).",
    )
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    engine = create_engine(db_url)

    with engine.connect() as conn:
        count = conn.execute(text(_COUNT_SQL)).scalar()

    print(f"[DRY RUN] rows_to_delete = {count}")

    if count == 0:
        print("No duplicates found — nothing to do.")
        return

    if not args.apply:
        print("Re-run with --apply to execute DELETE.")
        return

    with engine.begin() as conn:
        conn.execute(text(_DELETE_SQL))

    print(f"[APPLY] Deleted {count} duplicate rows from project_core.property_value.")


if __name__ == "__main__":
    main()
