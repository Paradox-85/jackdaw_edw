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
    clean_string, normalize_to_id_code, get_ref_id, parse_bool
)

config = load_config()
DB_URL = get_db_engine_url(config)
MDR_FILE = config.get('storage', {}).get('doc_dataset_file')

@task(name="Sync MDR Documents (Optimized)")
def sync_mdr_task(run_id):
    logger = get_run_logger()
    engine = create_engine(DB_URL)
    
    start_time = datetime.now()

    # --- PHASE 1: PRE-LOAD LOOKUPS & CACHES ---
    logger.info("Pre-loading document lookups and mapping caches...")
    with engine.connect() as conn:
        # Reference Caches (Normalized Code -> UUID)
        plant_lookup = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.plant"))}
        project_lookup = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.project"))}
        area_lookup = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.area"))}
        company_lookup = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.company"))}
        po_lookup = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.purchase_order"))}
        
        # Existing Documents (doc_number -> (id, row_hash, sync_status))
        doc_cache = {row[0]: (row[1], row[2], row[3]) for row in conn.execute(
            text("SELECT doc_number, id, row_hash, sync_status FROM project_core.document"))}
        
        # Mapping Cache: (doc_uuid, po_uuid) -> (mapping_id, sync_status)
        po_map_cache = {(row[0], row[1]): (row[2], row[3]) for row in conn.execute(
            text("SELECT document_id, po_id, id, sync_status FROM mapping.document_po"))}

    df = pd.read_excel(MDR_FILE, sheet_name=0, dtype=str, na_filter=False).dropna(subset=['DOCUMENT_NUMBER'])
    stats = {"New": 0, "Updated": 0, "No Changes": 0, "Errors": 0}

    # Step 1: Audit
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO audit_core.sync_run_stats (run_id, target_table, start_time, source_file)
            VALUES (:rid, 'project_core.document', :st, :src)
        """), {"rid": run_id, "st": start_time, "src": os.path.basename(MDR_FILE)})
        conn.commit()

    # --- PHASE 2: UNIFIED TRANSACTION PROCESSING ---
    with engine.begin() as conn:
        for _, row in df.iterrows():
            try:
                doc_num = clean_string(row['DOCUMENT_NUMBER'])
                doc_title = clean_string(row['DOCUMENT_TITLE'])
                mdr_flag = parse_bool(row.get('MDR'))
                curr_hash = calculate_row_hash(row)

                # Rev Date conversion
                raw_rev_date = clean_string(row.get('REVISION_DATE'))
                rev_date_val = None
                if raw_rev_date:
                    try:
                        rev_date_val = pd.to_datetime(raw_rev_date).date()
                    except: pass

                # Check Cache
                existing = doc_cache.get(doc_num)
                doc_uuid = None

                if existing:
                    doc_uuid, old_hash, old_sync_status = existing
                    if old_hash == curr_hash:
                        sync_status = "No Changes"
                        if old_sync_status in ['New', 'Updated', 'Deleted']:
                            conn.execute(text("UPDATE project_core.document SET sync_status = 'No Changes', sync_timestamp = :ts WHERE id = :id"),
                                         {"ts": datetime.now(), "id": doc_uuid})
                    else:
                        sync_status = "Updated"
                        # Use cached lookups or resolve via common if missing
                        plid = plant_lookup.get(clean_string(row.get('PLANT_CODE'))) or get_ref_id(conn, 'reference_core', 'plant', row.get('PLANT_CODE'), logger)
                        prid = project_lookup.get(clean_string(row.get('PROJECT_CODE'))) or get_ref_id(conn, 'reference_core', 'project', row.get('PROJECT_CODE'), logger)

                        #company can be looked up by normalized code or by name (with normalization) to handle discrepancies
                        co_raw = clean_string(row.get('COMPANY_NAME'))
                        coid = company_lookup.get(normalize_to_id_code(co_raw)) or get_ref_id(conn, 'reference_core', 'company', co_raw, logger, search_by='code', use_normalization=True)

                        conn.execute(text("""
                            UPDATE project_core.document SET 
                                title = :title, mdr_flag = :mdr, rev = :rev, rev_date = :rd, 
                                rev_comment = :rc, rev_author = :ra, doc_type_code = :dtc,
                                status = :stat, company_id = :coid, company_name_raw = :co_raw, plant_id = :plid, 
                                project_id = :prid, row_hash = :h, sync_status = :ss, sync_timestamp = :ts, object_status = 'Active'
                            WHERE id = :id
                        """), {
                            "title": doc_title, "mdr": mdr_flag, "rev": clean_string(row.get('REVISION_CODE')),
                            "rd": rev_date_val, "rc": clean_string(row.get('REVISION_COMMENT')),
                            "ra": clean_string(row.get('REVISION_AUTHOR')), "dtc": clean_string(row.get('DOCUMENT_TYPE_CODE')),
                            "stat": clean_string(row.get('DOCUMENT_STATUS')), "coid": coid, "co_raw": co_raw, "plid": plid, "prid": prid, 
                            "h": curr_hash, "ss": sync_status, "ts": datetime.now(), "id": doc_uuid
                        })
                else:
                    sync_status = "New"
                    plid = plant_lookup.get(clean_string(row.get('PLANT_CODE'))) or get_ref_id(conn, 'reference_core', 'plant', row.get('PLANT_CODE'), logger)
                    prid = project_lookup.get(clean_string(row.get('PROJECT_CODE'))) or get_ref_id(conn, 'reference_core', 'project', row.get('PROJECT_CODE'), logger)

                    co_raw = clean_string(row.get('COMPANY_NAME'))
                    coid = company_lookup.get(normalize_to_id_code(co_raw)) or get_ref_id(conn, 'reference_core', 'company', co_raw, logger, search_by='code', use_normalization=True)

                    doc_uuid = conn.execute(text("""
                        INSERT INTO project_core.document (
                            doc_number, title, rev, rev_date, rev_comment, rev_author, doc_type_code, mdr_flag, 
                            status, plant_id, project_id, company_id, company_name_raw, row_hash, sync_status, sync_timestamp, object_status
                        ) VALUES (
                            :dn, :title, :rev, :rd, :rc, :ra, :dtc, :mdr, :stat, :plid, :prid, :coid, :co_raw, :h, :ss, :ts, 'Active'
                        ) RETURNING id
                    """), {
                        "dn": doc_num, "title": doc_title, "rev": clean_string(row.get('REVISION_CODE')),
                        "rd": rev_date_val, "rc": clean_string(row.get('REVISION_COMMENT')),
                        "ra": clean_string(row.get('REVISION_AUTHOR')), "dtc": clean_string(row.get('DOCUMENT_TYPE_CODE')),
                        "mdr": mdr_flag, "stat": clean_string(row.get('DOCUMENT_STATUS')),
                        "plid": plid, "prid": prid, "coid": coid, "co_raw": co_raw,
                        "h": curr_hash, "ss": sync_status, "ts": datetime.now()
                    }).scalar()

                stats[sync_status] += 1

                # --- Optimized PO Mapping Block ---
                po_raw = clean_string(row.get('PO_CODE'))
                if po_raw and doc_uuid:
                    for pc in [c.strip() for c in po_raw.split(' ') if c.strip()]:
                        # Try cache first, then DB
                        po_id = po_lookup.get(normalize_to_id_code(pc)) or get_ref_id(conn, 'reference_core', 'purchase_order', pc, logger, use_normalization=True)
                        if po_id:
                            link_hash = calculate_row_hash(pd.Series([str(doc_uuid), str(po_id)]))
                            map_info = po_map_cache.get((doc_uuid, po_id))
                            
                            if not map_info:
                                conn.execute(text("INSERT INTO mapping.document_po (document_id, po_id, row_hash, sync_status, sync_timestamp) VALUES (:did, :pid, :h, 'New', :ts)"),
                                             {"did": doc_uuid, "pid": po_id, "h": link_hash, "ts": datetime.now()})
                            elif map_info[1] in ['New', 'Updated', 'Deleted']:
                                conn.execute(text("UPDATE mapping.document_po SET sync_status = 'No Changes', sync_timestamp = :ts, row_hash = :h WHERE id = :id"),
                                             {"ts": datetime.now(), "id": map_info[0], "h": link_hash})

            except Exception as e:
                stats["Errors"] += 1
                logger.error(f"Error at Doc {row.get('DOCUMENT_NUMBER')}: {e}")

    # Step 3: Final Bulk Cleanup
    with engine.begin() as conn:
        for table in ["project_core.document", "mapping.document_po"]:
            conn.execute(text(f"UPDATE {table} SET sync_status = 'Deleted' WHERE sync_timestamp < :run_start AND sync_status != 'Deleted'"),
                         {"run_start": start_time})

    # Step 4: Audit Record
    with engine.begin() as conn:
        conn.execute(text("UPDATE audit_core.sync_run_stats SET end_time = :et, count_created = :nc, count_updated = :nu, count_unchanged = :nch, count_errors = :ne WHERE run_id = :rid"),
                     {"rid": run_id, "et": datetime.now(), "nc": stats["New"], "nu": stats["Updated"], "nch": stats["No Changes"], "ne": stats["Errors"]})

@flow(name="MDR Document Sync")
def mdr_sync_flow():
    sync_mdr_task(str(uuid.uuid4()))

if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    mdr_sync_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/import_doc_data_deploy.py:mdr_sync_flow",
    ).deploy(
        name="doc-sync-deployment",
        work_pool_name="default-agent-pool",
    )