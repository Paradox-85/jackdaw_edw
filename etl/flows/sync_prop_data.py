import pandas as pd
import os
import sys
import uuid
from pathlib import Path
from sqlalchemy import create_engine, text
from prefect import flow, task, get_run_logger
from datetime import datetime

# Setup paths
current_dir = Path(__file__).resolve().parent
script_root = current_dir.parent
if str(script_root) not in sys.path:
    sys.path.append(str(script_root))

from tasks.common import (
    load_config, get_db_engine_url, calculate_row_hash,
    clean_string, normalize_to_id_code
)

config = load_config()
DB_URL = get_db_engine_url(config)
FILE_PATH = config.get('storage', {}).get('prop_dataset_file')

@task(name="Sync Property Values (Strict & High Perf)")
def sync_properties_task(run_id):
    logger = get_run_logger()
    
    if not FILE_PATH:
        raise ValueError("Config key 'prop_value_dataset_file' is missing!")

    engine = create_engine(DB_URL)
    start_time = datetime.now()
    
    # --- PHASE 1: PRE-LOAD LOOKUPS (Memory Cache) ---
    logger.info("Pre-loading lookups for property resolution...")
    with engine.connect() as conn:
        # Tag resolution: (source_id, tag_name) -> UUID
        tag_lookup = {(row[0], row[1]): row[2] for row in conn.execute(
            text("SELECT source_id, tag_name, id FROM project_core.tag"))}
        
        # Class resolution: code -> UUID (no normalization)
        class_lookup = {row[0]: row[1] for row in conn.execute(
            text("SELECT code, id FROM ontology_core.class"))}
        
        # Property resolution: UPPER(code) -> UUID (to handle OL_weight content case)
        prop_lookup = {str(row[0]).upper(): row[1] for row in conn.execute(
            text("SELECT code, id FROM ontology_core.property"))}
            
        # Class-Property Mapping: (class_uuid, prop_uuid) -> UUID
        cp_lookup = {(row[0], row[1]): row[2] for row in conn.execute(
            text("SELECT class_id, property_id, id FROM ontology_core.class_property"))}

        # Value existence cache: (tag_source_id_raw, property_code_raw) -> (id, row_hash, sync_status)
        val_cache = {(row[0], row[1]): (row[2], row[3], row[4]) for row in conn.execute(
            text("SELECT tag_source_id_raw, property_code_raw, id, row_hash, sync_status FROM project_core.property_value"))}

    # --- PHASE 2: READ EXCEL (Disable NA Filtering) ---
    # na_filter=False ensures "NA" is treated as a string, not as a missing value
    df = pd.read_excel(FILE_PATH, sheet_name=0, dtype=str, na_filter=False)
    
    # Remove truly empty rows where Tag Id is missing or just whitespace
    df = df[df['Tag Id'].str.strip() != '']
    
    stats = {"New": 0, "Updated": 0, "No Changes": 0, "Errors": 0}
    filename = os.path.basename(FILE_PATH)

    # Initial Audit Record
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO audit_core.sync_run_stats (run_id, target_table, start_time, source_file)
            VALUES (:rid, 'project_core.property_value', :st, :src)
        """), {"rid": run_id, "st": start_time, "src": filename})
        conn.commit()

    # --- PHASE 3: PROCESSING (Unified Transaction) ---
    logger.info(f"Synchronizing {len(df)} records...")
    with engine.begin() as conn:
        for _, row in df.iterrows():
            try:
                # 1. Extraction (literal strings because of na_filter=False)
                tag_sid_raw = row.get('Tag Id').strip() or None
                tag_name_raw = row.get('Tag Name').strip() or None
                class_code_raw = row.get('RDL Class Id').strip() or None
                prop_code_raw = row.get('RDL Property Id').strip() or None
                concept_raw = row.get('RDL Property Concept').strip() or None
                uom_raw = row.get('Property UoM').strip() or None
                p_value = row.get('Property Value').strip() or None # "NA" will be preserved here
                
                curr_hash = calculate_row_hash(row)

                # 2. Manual Resolution (Strict Mode)
                t_uuid = tag_lookup.get((tag_sid_raw, tag_name_raw)) if tag_sid_raw and tag_name_raw else None
                c_uuid = class_lookup.get(class_code_raw) if class_code_raw else None
                p_uuid = prop_lookup.get(prop_code_raw.upper()) if prop_code_raw else None
                m_uuid = cp_lookup.get((c_uuid, p_uuid)) if c_uuid and p_uuid else None

                params = {
                    "tid": t_uuid, "cid": c_uuid, "pid": p_uuid, "mid": m_uuid,
                    "tnr": tag_name_raw, "ccr": class_code_raw, "pcr": prop_code_raw,
                    "mcr": concept_raw, "uom": uom_raw, "val": p_value,
                    "h": curr_hash, "ts": datetime.now(),
                    "tsr": tag_sid_raw
                }

                # 3. Cache-based UPSERT logic
                existing = val_cache.get((tag_sid_raw, prop_code_raw))

                if existing:
                    val_uuid, old_hash, old_sync_status = existing
                    if old_hash == curr_hash:
                        sync_status = "No Changes"
                        if old_sync_status != 'No Changes':
                            conn.execute(text("UPDATE project_core.property_value SET sync_status='No Changes', sync_timestamp=:ts WHERE id=:id"), 
                                         {"ts": datetime.now(), "id": val_uuid})
                    else:
                        sync_status = "Updated"
                        params["id"] = val_uuid; params["ss"] = sync_status
                        conn.execute(text("""
                            UPDATE project_core.property_value SET
                                tag_id=:tid, class_id=:cid, property_id=:pid, mapping_id=:mid,
                                tag_name_raw=:tnr, class_code_raw=:ccr, property_code_raw=:pcr,
                                mapping_concept_raw=:mcr, property_uom_raw=:uom, property_value=:val,
                                row_hash=:h, sync_status=:ss, sync_timestamp=:ts, object_status='Active'
                            WHERE id = :id
                        """), params)
                else:
                    sync_status = "New"
                    params["ss"] = sync_status
                    conn.execute(text("""
                        INSERT INTO project_core.property_value (
                            tag_id, class_id, property_id, mapping_id, tag_name_raw, class_code_raw,
                            property_code_raw, mapping_concept_raw, property_uom_raw, property_value,
                            row_hash, sync_status, sync_timestamp, object_status, tag_source_id_raw
                        ) VALUES (
                            :tid, :cid, :pid, :mid, :tnr, :ccr, :pcr, :mcr, :uom, :val, :h, :ss, :ts, 'Active', :tsr
                        )
                    """), params)

                stats[sync_status] += 1

            except Exception as e:
                stats["Errors"] += 1
                logger.error(f"Error at Tag {row.get('Tag Name')} / Prop {row.get('RDL Property Id')}: {e}")

    # --- PHASE 4: CLEANUP & AUDIT ---
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE project_core.property_value SET sync_status = 'Deleted', object_status = 'Inactive'
            WHERE sync_timestamp < :run_start AND sync_status != 'Deleted'
        """), {"run_start": start_time})

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE audit_core.sync_run_stats SET end_time = :et, count_created = :nc, count_updated = :nu, 
            count_unchanged = :nch, count_errors = :ne WHERE run_id = :rid
        """), {
            "rid": run_id, "et": datetime.now(), "nc": stats["New"], "nu": stats["Updated"], 
            "nch": stats["No Changes"], "ne": stats["Errors"]
        })

@flow(name="Property Values Sync")
def properties_sync_flow():
    rid = str(uuid.uuid4())
    sync_properties_task(rid)

if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent.parent)
    properties_sync_flow.serve(name="prop-sync-deployment")