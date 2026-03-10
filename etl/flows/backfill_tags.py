import os
import re
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime
from prefect import flow, get_run_logger

# Add project root to path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from flows.sync_tag_data import sync_tags_task, build_hierarchy

# Historical data path
HISTORY_DIR = "/mnt/shared-data/ram-user/Jackdaw/Master-Data/_master/data/_history"
FILE_MASK = r"MTR-dataset-(\d{4}-\d{2}-\d{2})_\d{2}\.xlsx"

def get_sorted_history():
    """ Scans directory and returns sorted list of historical file info """
    if not os.path.exists(HISTORY_DIR):
        return []

    history = []
    for fname in os.listdir(HISTORY_DIR):
        match = re.match(FILE_MASK, fname)
        if match:
            fdate = datetime.strptime(match.group(1), "%Y-%m-%d")
            history.append({
                "path": os.path.join(HISTORY_DIR, fname),
                "date": fdate,
                "name": fname
            })
    return sorted(history, key=lambda x: x['date'])


def get_quarterly_sample(all_files):
    """Select representative files: always first & last, plus first file of each quarter in between.

    Quarter mapping: Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec.
    """
    if len(all_files) <= 2:
        return all_files

    first = all_files[0]
    last = all_files[-1]

    seen_quarters = set()
    quarterly_firsts = []
    for f in all_files[1:-1]:
        q = (f['date'].month - 1) // 3 + 1  # 1..4
        key = (f['date'].year, q)
        if key not in seen_quarters:
            seen_quarters.add(key)
            quarterly_firsts.append(f)

    seen_paths = set()
    result = []
    for f in [first] + quarterly_firsts + [last]:
        if f['path'] not in seen_paths:
            seen_paths.add(f['path'])
            result.append(f)
    return result

@flow(name="Tag History Replay (Backfill)", log_prints=True)
def tag_backfill_flow(debug_mode: bool = True):
    logger = get_run_logger()
    all_files = get_sorted_history()
    
    if not all_files:
        logger.error(f"No historical MTR files found in {HISTORY_DIR}!")
        return

    # Determine files to process
    targets = [all_files[0], all_files[-1]] if debug_mode and len(all_files) > 1 else get_quarterly_sample(all_files)
    total = len(targets)

    logger.info(f"STARTING BACKFILL: Mode={'DEBUG' if debug_mode else 'FULL'}")
    logger.info(f"Total snapshots to replay: {total} (quarterly sample from {len(all_files)} available files)")

    # PHASE 1: Sequential Data Sync (UPSERT only)
    for index, f_info in enumerate(targets, 1):
        start_ts = time.time()
        
        # Generate stable UUID based on filename
        NAMESPACE_BACKFILL = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        run_id = str(uuid.uuid5(NAMESPACE_BACKFILL, f_info['name']))
        
        logger.info(f"[{index}/{total}] Replaying data from: {f_info['name']}")
        
        try:
            # Sync core tags and mappings without building hierarchy yet
            sync_tags_task(
                run_id=run_id, 
                override_file=f_info['path'], 
                override_date=f_info['date']
            )
            
            duration = time.time() - start_ts
            logger.info(f"Step {index} OK: Sync completed in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"STEP FAILED: {f_info['name']} Error: {e}")
            if debug_mode: raise e

    # PHASE 2: Final Hierarchy Resolution
    # We only run this once for the MOST RECENT file processed to set current parent-child links
    logger.info("PHASE 2: Resolving Final Parent-Child Hierarchy...")
    final_file = targets[-1]['path']
    build_hierarchy(override_file=final_file)

    logger.info("========================================")
    logger.info("BACKFILL PROCESS COMPLETED SUCCESSFULLY")
    logger.info("========================================")

if __name__ == "__main__":
    # Start with debug_mode=True to test the first and last files
    tag_backfill_flow(debug_mode=True)