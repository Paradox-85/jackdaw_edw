import uuid
import os
import sys
from pathlib import Path
from prefect import flow, get_run_logger

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Import your tasks from the respective files
# Ensure your task files are in the python path
try:
    from flows.sync_doc_data import sync_mdr_task
    from flows.sync_tag_data import sync_tags_task
    from flows.sync_tag_data import build_hierarchy
    from flows.sync_prop_data import sync_properties_task
except ImportError as e:
    print(f"Error: Could not find sync files. Check filenames in /flows/ folder. Details: {e}")
    sys.exit(1)

@flow(name="Project Master Data Sync", 
      description="SEQUENTIAL PIPELINE: 1. Documents -> 2. Tags -> 3. Hierarchy -> 4. Property Values")
def main_sync_flow():
    logger = get_run_logger()
    
    # Generate a common Run ID for cross-table audit tracking
    common_run_id = str(uuid.uuid4())
    
    logger.info(f"Starting Integrated Master Sync Pipeline | Run ID: {common_run_id}")

    # STEP 1: Sync Documents (MDR)
    # Required first because Tags reference these documents
    logger.info(">>> Step 1/4: Syncing MDR Documents...")
    sync_mdr_task(run_id=common_run_id)
    
    # STEP 2: Sync Tags (MTR)
    # Required before Hierarchy and Property Values
    logger.info(">>> Step 2/4: Syncing MTR Tags and Mappings...")
    sync_tags_task(run_id=common_run_id)

    # STEP 3: Resolve Hierarchy
    # Links parent tags to child tags within project_core.tag
    logger.info(">>> Step 3/4: Resolving Parent-Child Hierarchy...")
    build_hierarchy()

    # STEP 4: Sync Property Values (Attributes)
    # Final step: Populates the project_core.property_value table
    logger.info(">>> Step 4/4: Syncing RDL Property Values...")
    sync_properties_task(run_id=common_run_id)

    logger.info("Integrated Master Sync Pipeline completed successfully.")

if __name__ == "__main__":
    main_sync_flow.from_source(
        source="/mnt/shared-data/ram-user/Jackdaw/prefect-worker/scripts",
        entrypoint="etl/flows/main_sync.py:main_sync_flow",
    ).deploy(
        name="sequential-master-sync",
        work_pool_name="default-agent-pool",
        tags=["production", "master-data", "integrated-pipeline"],
    )