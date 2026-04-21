import os
import re
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime
from prefect import flow, get_run_logger

# Add project root to path — scripts/ → repo root
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parent.parent  # scripts/ → repo root
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from etl.flows.import_tag_data_deploy import sync_tags_task, build_hierarchy
from etl.tasks.common import load_config

_config = load_config()

# Historical snapshots — directory with dated MTR files
HISTORY_DIR = _config.get("storage", {}).get(
    "history_dir",
    "/mnt/shared-data/ram-user/Jackdaw/Master-Data/_master/data/_history",
)
FILE_MASK = r"MTR-dataset-(\d{4}-\d{2}-\d{2})_\d{2}\.xlsx"

# Production master file — same path used by import_tag_data_deploy flow
MASTER_FILE = _config.get("storage", {}).get("tag_dataset_file")


def get_sorted_history(target_date: str | None = None) -> list[dict]:
    """Scan HISTORY_DIR and return sorted file info dicts.

    Args:
        target_date: Optional ISO date string "YYYY-MM-DD". When provided,
            returns only files whose embedded date matches exactly.

    Returns:
        List of dicts with keys: path, date, name — sorted by date ascending.
    """
    if not os.path.exists(HISTORY_DIR):
        return []

    history = []
    for fname in os.listdir(HISTORY_DIR):
        match = re.match(FILE_MASK, fname)
        if not match:
            continue
        file_date_str = match.group(1)
        if target_date and file_date_str != target_date:
            continue
        fdate = datetime.strptime(file_date_str, "%Y-%m-%d")
        history.append({
            "path": os.path.join(HISTORY_DIR, fname),
            "date": fdate,
            "name": fname,
        })
    return sorted(history, key=lambda x: x["date"])


def get_monthly_sample(all_files: list[dict], step_months: int = 3) -> list[dict]:
    """Select representative files: always first & last, plus first file of each
    N-month bucket in between.

    step_months=1 → monthly (one file per calendar month)
    step_months=2 → bi-monthly (one file per 2-month window)
    step_months=3 → quarterly (one file per quarter, matches old behaviour)

    A bucket key is defined as: (year * 12 + month - 1) // step_months
    This ensures consistent, non-overlapping buckets regardless of step size.
    """
    if len(all_files) <= 2:
        return all_files

    first = all_files[0]
    last = all_files[-1]

    seen_buckets: set = set()
    sampled = []
    for f in all_files[1:-1]:
        month_index = f["date"].year * 12 + f["date"].month - 1
        bucket = month_index // step_months
        if bucket not in seen_buckets:
            seen_buckets.add(bucket)
            sampled.append(f)

    seen_paths: set = set()
    result = []
    for f in [first] + sampled + [last]:
        if f["path"] not in seen_paths:
            seen_paths.add(f["path"])
            result.append(f)
    return result


@flow(name="Tag History Replay (Backfill)", log_prints=True)
def tag_backfill_flow(
    mode: str = "history",
    debug_mode: bool = True,
    step_months: int = 3,
    target_date: str | None = None,
):
    """Replay tag sync for historical snapshots or run once against the production master file.

    Args:
        mode: "history" — scan HISTORY_DIR and replay dated snapshots;
              "master"  — single run against the production master file (FILE_PATH from config).
        debug_mode: History mode only. When True and target_date is None,
            processes only the first and last available files.
            Ignored when target_date is set or mode="master".
        step_months: History mode only. Sampling step in months (1, 2, 3, ...).
            Controls how many calendar months each sample bucket covers.
            1 = monthly, 2 = bi-monthly, 3 = quarterly (default).
            Ignored when target_date is set or debug_mode=True.
        target_date: History mode only. ISO date string "YYYY-MM-DD".
            When provided, only files whose filename date matches are processed.
            Overrides debug_mode selection logic.
    """
    logger = get_run_logger()
    NAMESPACE_BACKFILL = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

    # ── MASTER MODE ──────────────────────────────────────────────────────────
    if mode == "master":
        if not MASTER_FILE:
            logger.error("storage.tag_dataset_file is not set in config.yaml — cannot run master mode.")
            return

        master_name = Path(MASTER_FILE).name
        run_id = str(uuid.uuid5(NAMESPACE_BACKFILL, master_name))

        logger.info("STARTING SYNC: mode=MASTER")
        logger.info(f"File: {master_name}")

        start_ts = time.time()
        try:
            # override_file/override_date omitted — task uses FILE_PATH and datetime.now()
            sync_tags_task(run_id=run_id)
            logger.info(f"Sync completed in {time.time() - start_ts:.2f}s")
        except Exception as e:
            logger.error(f"SYNC FAILED: {e}")
            raise

        logger.info("Resolving Parent-Child Hierarchy...")
        build_hierarchy()

        logger.info("==============================")
        logger.info("MASTER SYNC COMPLETED")
        logger.info("==============================")
        return

    # ── HISTORY MODE ─────────────────────────────────────────────────────────
    all_files = get_sorted_history(target_date=target_date)

    if not all_files:
        if target_date:
            logger.error(f"No MTR files found for date {target_date!r} in {HISTORY_DIR}")
        else:
            logger.error(f"No historical MTR files found in {HISTORY_DIR}")
        return

    # Determine target subset
    if target_date:
        targets = all_files  # already filtered — use all matching files
        mode_label = f"DATE={target_date}"
    elif debug_mode and len(all_files) > 1:
        targets = [all_files[0], all_files[-1]]
        mode_label = "DEBUG (first + last)"
    else:
        targets = get_monthly_sample(all_files, step_months=step_months)
        step_label = {1: "monthly", 2: "bi-monthly", 3: "quarterly"}.get(
            step_months, f"{step_months}-month"
        )
        mode_label = f"FULL ({step_label} sample, step={step_months}mo)"

    total = len(targets)
    logger.info(f"STARTING BACKFILL: mode=HISTORY/{mode_label}")
    logger.info(f"Snapshots to replay: {total} (from {len(all_files)} available)")

    # PHASE 1: Sequential tag sync (UPSERT only, no hierarchy)
    for index, f_info in enumerate(targets, 1):
        start_ts = time.time()
        run_id = str(uuid.uuid5(NAMESPACE_BACKFILL, f_info["name"]))
        logger.info(f"[{index}/{total}] {f_info['name']}")
        try:
            sync_tags_task(
                run_id=run_id,
                override_file=f_info["path"],
                override_date=f_info["date"],
            )
            logger.info(f"  OK — {time.time() - start_ts:.2f}s")
        except Exception as e:
            logger.error(f"  FAILED: {e}")
            if debug_mode or target_date:
                raise

    # PHASE 2: Hierarchy resolution — run once against the most recent processed file
    logger.info("Resolving Final Parent-Child Hierarchy...")
    build_hierarchy(override_file=targets[-1]["path"])

    logger.info("========================================")
    logger.info("BACKFILL PROCESS COMPLETED SUCCESSFULLY")
    logger.info("========================================")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tag backfill / master sync runner")
    parser.add_argument(
        "--mode", choices=["history", "master"], default="history",
        help="'history' — replay dated snapshots; 'master' — run against production file",
    )
    parser.add_argument(
        "--date", default=None, metavar="YYYY-MM-DD",
        help="History mode: process only files matching this date",
    )
    parser.add_argument(
        "--no-debug", dest="debug_mode", action="store_false",
        help="History mode: run full quarterly sample instead of first+last only",
    )
    parser.add_argument(
        "--step", dest="step_months", type=int, default=3,
        metavar="N",
        help="History mode: sampling step in months (1=monthly, 2=bi-monthly, 3=quarterly). Default: 3",
    )
    parser.set_defaults(debug_mode=True)
    args = parser.parse_args()

    tag_backfill_flow(
        mode=args.mode,
        debug_mode=args.debug_mode,
        step_months=args.step_months,
        target_date=args.date,
    )
