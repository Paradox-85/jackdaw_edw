#!/usr/bin/env python3
"""
Cleanup old EIS export subdirectories.

Structure: {EIS_EXPORT_DIR}/{REVISION}/{YYYYMMDD_HHMM}/
Deletes session subdirectory trees older than --days (default 7).
Removes empty revision parent directories after cleanup.

Cron example (daily at 02:00):
    0 2 * * * /usr/bin/python3 /mnt/shared-data/ram-user/Jackdaw/EDW-repository/scripts/cleanup_eis_exports.py

Usage:
    python cleanup_eis_exports.py [--export-dir PATH] [--days 7] [--dry-run]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_EXPORT_DIR = "/mnt/shared-data/ram-user/Jackdaw/Export/EIS"
DEFAULT_DAYS = 7


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--export-dir", default=DEFAULT_EXPORT_DIR,
                   help=f"EIS export root directory (default: {DEFAULT_EXPORT_DIR})")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS,
                   help=f"Delete session folders older than N days (default: {DEFAULT_DAYS})")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would be deleted without actually deleting")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    base = Path(args.export_dir)

    if not base.exists():
        print(f"[WARN] Export dir not found: {base}")
        sys.exit(0)

    cutoff = datetime.now() - timedelta(days=args.days)
    deleted = 0
    mode = "[DRY-RUN]" if args.dry_run else ""

    # Walk: base/{REV}/{YYYYMMDD_HHMM}/
    for rev_dir in sorted(base.iterdir()):
        if not rev_dir.is_dir():
            continue
        for session_dir in sorted(rev_dir.iterdir()):
            if not session_dir.is_dir():
                continue
            mtime = datetime.fromtimestamp(session_dir.stat().st_mtime)
            if mtime < cutoff:
                age_days = (datetime.now() - mtime).days
                print(f"{mode} {'Would delete' if args.dry_run else 'Deleting'}: "
                      f"{session_dir}  (age {age_days}d, mtime {mtime:%Y-%m-%d %H:%M})")
                if not args.dry_run:
                    shutil.rmtree(session_dir)
                    deleted += 1
                    # Remove empty revision parent
                    if not any(rev_dir.iterdir()):
                        rev_dir.rmdir()
                        print(f"  Removed empty revision dir: {rev_dir}")

    summary = "Would delete" if args.dry_run else "Deleted"
    print(f"\nDone. {summary} {deleted} session folder(s) older than {args.days} day(s).")


if __name__ == "__main__":
    main()
