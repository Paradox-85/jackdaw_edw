import json
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
    clean_string, normalize_to_id_code, to_dt
)

config = load_config()
DB_URL = get_db_engine_url(config)
FILE_PATH = config.get('storage', {}).get('tag_dataset_file')


@task(name="Sync Tags and Mappings (High-Speed Batch Mode)")
def sync_tags_task(run_id, override_file=None, override_date=None):
    logger = get_run_logger()
    engine = create_engine(DB_URL)
    sync_time = override_date if override_date else datetime.now()
    current_file = override_file if override_file else FILE_PATH
    execution_start = datetime.now()

    # --- PHASE 1: PRE-LOAD EVERYTHING ---
    logger.info("PHASE 1: Pre-loading registries into memory...")
    with engine.connect() as conn:
        # source_id is the stable system key; tag_name may change across syncs
        tag_registry = {row[1]: (row[2], row[3], row[4]) for row in conn.execute(
            text("SELECT tag_name, source_id, id, row_hash, sync_status FROM project_core.tag"))}
        doc_lookup = {row[0]: row[1] for row in conn.execute(text("SELECT doc_number, id FROM project_core.document"))}
        sece_lookup = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.sece"))}
        company_lookup = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.company"))}
        project_lookup = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.project"))}
        article_lookup = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.article"))}
        plant_lookup   = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.plant"))}
        class_lookup   = {row[0]: row[1] for row in conn.execute(text("SELECT name, id FROM ontology_core.class"))}
        po_lookup      = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.purchase_order"))}
        unit_lookup    = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.process_unit"))}
        area_lookup    = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.area"))}
        disc_lookup    = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.discipline"))}
        model_lookup   = {row[0]: row[1] for row in conn.execute(text("SELECT code, id FROM reference_core.model_part"))}
        tag_doc_cache = {(row[0], row[1]): (row[2], row[3]) for row in conn.execute(
            text("SELECT tag_id, document_id, id, sync_status FROM mapping.tag_document"))}
        tag_sece_cache = {(row[0], row[1]): (row[2], row[3]) for row in conn.execute(
            text("SELECT tag_id, sece_id, id, sync_status FROM mapping.tag_sece"))}
        # Load previous hash + snapshot to detect field count changes (Extended/Reduced)
        history_data_cache = {row[0]: (row[1], row[2]) for row in conn.execute(text("""
            SELECT DISTINCT ON (tag_id) tag_id, row_hash, snapshot
            FROM audit_core.tag_status_history
            WHERE row_hash IS NOT NULL
            ORDER BY tag_id, sync_timestamp DESC
        """))}

    df = pd.read_excel(current_file, sheet_name=0, dtype=str, na_filter=False).dropna(subset=['TAG_NAME', 'ID'])
    
    tags_to_update = []
    tags_status_only = []
    doc_maps_to_insert = []
    doc_maps_to_update = []
    sece_maps_to_insert = []
    sece_maps_to_update = []
    history_to_insert = []
    stats = {"New": 0, "Updated": 0, "Extended": 0, "Reduced": 0, "No Changes": 0, "Errors": 0}

    def _field_count(snap_json: str | None) -> int:
        """Count non-null fields in a JSON snapshot string."""
        if not snap_json:
            return 0
        try:
            return len(json.loads(snap_json))
        except Exception:
            return 0

    # --- PHASE 2 & 4 MERGED: ONE TRANSACTION FOR EVERYTHING ---
    logger.info("PHASE 2: Processing and executing in a single atomic transaction...")
    
    # We open ONE transaction block that covers the entire loop and all bulk updates
    with engine.begin() as conn:
        for _, row in df.iterrows():
            try:
                tn, sid = clean_string(row['TAG_NAME']), clean_string(row['ID'])
                curr_hash = calculate_row_hash(row)
                
                # Resolve references — all in-memory lookups, zero per-row SQL
                design_co_raw_val = clean_string(row.get('DESIGNED_BY_COMPANY_NAME'))
                mfr_id        = company_lookup.get(normalize_to_id_code(row.get('MANUFACTURER_COMPANY_NAME')))
                vendor_id     = company_lookup.get(normalize_to_id_code(row.get('VENDOR_COMPANY_NAME')))
                design_co_id  = company_lookup.get(normalize_to_id_code(design_co_raw_val))
                project_id    = project_lookup.get('JDAW')
                plant_id      = plant_lookup.get(clean_string(row.get('PLANT_CODE')))
                article_id    = article_lookup.get(normalize_to_id_code(row.get('ARTICLE_CODE')))
                model_id      = model_lookup.get(normalize_to_id_code(row.get('MODEL_PART_NAME')))
                class_id      = class_lookup.get(clean_string(row.get('TAG_CLASS_NAME')))
                po_id         = po_lookup.get(normalize_to_id_code(row.get('PO_CODE')))
                unit_id       = unit_lookup.get(clean_string(row.get('PROCESS_UNIT_CODE')))
                area_id       = area_lookup.get(clean_string(row.get('AREA_CODE')))
                disc_id       = disc_lookup.get(clean_string(row.get('DISCIPLINE_CODE')))

                params = {
                    "tn": tn, "sid": sid, "h": curr_hash, "ts": sync_time,
                    "t_stat": clean_string(row.get('TAG_STATUS')),
                    "cls_raw": clean_string(row.get('TAG_CLASS_NAME')),
                    "art_raw": clean_string(row.get('ARTICLE_CODE')),
                    "dco_raw": design_co_raw_val,
                    "area_raw": clean_string(row.get('AREA_CODE')),
                    "unit_raw": clean_string(row.get('PROCESS_UNIT_CODE')),
                    "plt_raw": clean_string(row.get('PLANT_CODE')),
                    "disc_raw": clean_string(row.get('DISCIPLINE_CODE')),
                    "po_raw": clean_string(row.get('PO_CODE')),
                    "eq": f"Equip_{tn}", "mfr": mfr_id, "vnd": vendor_id, "mod": model_id,
                    "sn": clean_string(row.get('MANUFACTURER_SERIAL_NUMBER')),
                    "tid": clean_string(row.get('TECHIDENTNO')),
                    "als": clean_string(row.get('ALIAS')),
                    "dsc": clean_string(row.get('TAG_DESCRIPTION')),
                    "inst": to_dt(row.get('INSTALLATION_DATE')) if pd.notna(row.get('INSTALLATION_DATE')) else None,
                    "start": to_dt(row.get('STARTUP_DATE')) if pd.notna(row.get('STARTUP_DATE')) else None,
                    "warn": to_dt(row.get('WARRANTY_END_DATE')) if pd.notna(row.get('WARRANTY_END_DATE')) else None,
                    "prc": clean_string(row.get('PRICE')),
                    "m_raw": clean_string(row.get('MODEL_PART_NAME')),
                    "mfr_raw": clean_string(row.get('MANUFACTURER_COMPANY_NAME')),
                    "v_raw": clean_string(row.get('VENDOR_COMPANY_NAME')),
                    "cls_id": class_id, "po_id": po_id, "u_id": unit_id, "a_id": area_id, "d_id": disc_id,
                    "art_id": article_id, "dco_id": design_co_id, "prj_id": project_id,
                    "prnt_raw": clean_string(row.get('PARENT_TAG_NAME')),
                    "ex_cls": clean_string(row.get('EX CLASS')),
                    "ip_gr": clean_string(row.get('IP_GRADE')),
                    "mc_pkg": clean_string(row.get('MC_PACKAGE_CODE')),
                    "from_tag_raw": clean_string(row.get('FROM_TAG')),
                    "to_tag_raw": clean_string(row.get('TO_TAG')),
                    # Export-facing fields for EIS Tag Register (seq 003)
                    "plt_id":  plant_id,
                    "sci":     clean_string(row.get('SAFETY_CRITICAL_ITEM')),
                    "sci_rea": clean_string(row.get('SAFETY_CRITICAL_ITEM _REASON_AWARDED')),
                    "pci":     clean_string(row.get('PRODUCTION_CRITICAL_ITEM')),
                }

                _SNAPSHOT_KEYS = {
                    "t_stat", "cls_raw", "art_raw", "dco_raw", "area_raw", "unit_raw", "plt_raw",
                    "disc_raw", "po_raw", "sn", "tid", "als", "dsc", "inst", "start",
                    "warn", "prc", "m_raw", "mfr_raw", "v_raw", "prnt_raw",
                    "ex_cls", "ip_gr", "mc_pkg", "from_tag_raw", "to_tag_raw",
                    "sci", "sci_rea", "pci",
                }
                snapshot = json.dumps({k: str(v) for k, v in params.items() if k in _SNAPSHOT_KEYS and v is not None})

                existing = tag_registry.get(sid)
                tag_uuid = None

                if existing:
                    tag_uuid = existing[0]
                    if existing[1] == curr_hash:
                        stats["No Changes"] += 1
                        tags_status_only.append({"ts": sync_time, "id": tag_uuid})
                        if existing[2] != 'No Changes':
                            history_to_insert.append({"tid": tag_uuid, "tn": tn, "sid": sid,
                                                       "ss": "No Changes", "ts": sync_time, "rid": run_id,
                                                       "h": curr_hash, "snap": snapshot})
                    else:
                        prev_hash, prev_snap = history_data_cache.get(tag_uuid, (None, None))
                        prev_count = _field_count(prev_snap)
                        curr_count = len(json.loads(snapshot))
                        if curr_count > prev_count:
                            sub_status = "Extended"
                        elif curr_count < prev_count:
                            sub_status = "Reduced"
                        else:
                            sub_status = "Updated"
                        stats[sub_status] += 1
                        params["id"] = tag_uuid
                        params["sub_status"] = sub_status
                        tags_to_update.append(params)
                        if curr_hash != prev_hash:
                            history_to_insert.append({"tid": tag_uuid, "tn": tn, "sid": sid,
                                                       "ss": sub_status, "ts": sync_time, "rid": run_id,
                                                       "h": curr_hash, "snap": snapshot})
                else:
                    stats["New"] += 1
                    # New tag is inserted immediately within the transaction to get ID
                    tag_uuid = conn.execute(text("""
                        INSERT INTO project_core.tag (
                            tag_name, source_id, row_hash, tag_status, sync_status, sync_timestamp,
                            tag_class_raw, article_code_raw, design_company_name_raw, area_code_raw,
                            process_unit_raw, plant_raw, discipline_code_raw, po_code_raw, equip_no, manufacturer_id,
                            vendor_id, model_id, serial_no, tech_id, alias, description, install_date,
                            startup_date, warranty_end_date, price, model_part_raw,
                            manufacturer_company_raw, vendor_company_raw, class_id, parent_tag_raw,
                            po_id, process_unit_id, area_id, discipline_id, article_id, design_company_id, project_id, object_status,
                            ex_class, ip_grade, mc_package_code, from_tag_raw, to_tag_raw,
                            plant_id, safety_critical_item, safety_critical_item_reason_awarded, production_critical_item
                        ) VALUES (
                            :tn, :sid, :h, :t_stat, 'New', :ts,
                            :cls_raw, :art_raw, :dco_raw, :area_raw, :unit_raw, :plt_raw, :disc_raw, :po_raw, :eq, :mfr,
                            :vnd, :mod, :sn, :tid, :als, :dsc, :inst, :start, :warn, :prc, :m_raw,
                            :mfr_raw, :v_raw, :cls_id, :prnt_raw, :po_id, :u_id, :a_id, :d_id, :art_id, :dco_id, :prj_id, 'Active',
                            :ex_cls, :ip_gr, :mc_pkg, :from_tag_raw, :to_tag_raw,
                            :plt_id, :sci, :sci_rea, :pci
                        ) RETURNING id
                    """), params).scalar()
                    history_to_insert.append({"tid": tag_uuid, "tn": tn, "sid": sid,
                                              "ss": "New", "ts": sync_time, "rid": run_id,
                                              "h": curr_hash, "snap": snapshot})

                if tag_uuid:
                    doc_raw = clean_string(row.get('TAG_DOC'))
                    if doc_raw:
                        for dc in [d.strip() for d in doc_raw.split(' ') if d.strip()]:
                            doc_id = doc_lookup.get(dc)
                            lh = calculate_row_hash(pd.Series([str(tag_uuid), str(doc_id or dc)]))
                            mi = tag_doc_cache.get((tag_uuid, doc_id))
                            if not mi:
                                doc_maps_to_insert.append({"tid": tag_uuid, "did": doc_id, "dcr": dc, "tnr": tn, "h": lh, "ts": sync_time})
                            elif mi[1] != 'No Changes':
                                doc_maps_to_update.append({"ts": sync_time, "h": lh, "dcr": dc, "tnr": tn, "id": mi[0], "did": doc_id})

                    sece_raw = clean_string(row.get('SAFETY_CRITICAL_ITEM _GROUP'))
                    if sece_raw:
                        for sc in [s.strip() for s in sece_raw.split(' ') if s.strip()]:
                            sece_id = sece_lookup.get(sc)
                            if sece_id:
                                slh = calculate_row_hash(pd.Series([str(tag_uuid), str(sece_id)]))
                                smi = tag_sece_cache.get((tag_uuid, sece_id))
                                if not smi:
                                    sece_maps_to_insert.append({"tid": tag_uuid, "sid": sece_id, "h": slh, "ts": sync_time})
                                elif smi[1] != 'No Changes':
                                    sece_maps_to_update.append({"ts": sync_time, "h": slh, "id": smi[0]})

            except Exception as e:
                stats["Errors"] += 1
                logger.error(f"Error at Tag {row.get('TAG_NAME')}: {e}")

        # --- EXECUTE BULK OPS (Still inside the same engine.begin() block) ---
        if tags_status_only:
            conn.execute(text("UPDATE project_core.tag SET sync_status='No Changes', sync_timestamp=:ts WHERE id=:id"), tags_status_only)
        
        if tags_to_update:
            conn.execute(text("""
                UPDATE project_core.tag SET
                    tag_name=:tn, tag_status=:t_stat, row_hash=:h, sync_status=:sub_status, sync_timestamp=:ts,
                    tag_class_raw=:cls_raw, article_code_raw=:art_raw, design_company_name_raw=:dco_raw,
                    area_code_raw=:area_raw, process_unit_raw=:unit_raw, plant_raw=:plt_raw, discipline_code_raw=:disc_raw,
                    po_code_raw=:po_raw, equip_no=:eq, manufacturer_id=:mfr, vendor_id=:vnd,
                    model_id=:mod, serial_no=:sn, tech_id=:tid, alias=:als, description=:dsc,
                    install_date=:inst, startup_date=:start, warranty_end_date=:warn, price=:prc,
                    model_part_raw=:m_raw, manufacturer_company_raw=:mfr_raw, vendor_company_raw=:v_raw,
                    class_id=:cls_id, po_id=:po_id, process_unit_id=:u_id, area_id=:a_id, parent_tag_raw=:prnt_raw,
                    discipline_id=:d_id, article_id=:art_id, design_company_id=:dco_id, project_id=:prj_id, object_status='Active',
                    ex_class=:ex_cls, ip_grade=:ip_gr, mc_package_code=:mc_pkg,
                    from_tag_raw=:from_tag_raw, to_tag_raw=:to_tag_raw,
                    plant_id=:plt_id, safety_critical_item=:sci,
                    safety_critical_item_reason_awarded=:sci_rea, production_critical_item=:pci
                WHERE id=:id
            """), tags_to_update)

        if doc_maps_to_insert:
            conn.execute(text("""
                INSERT INTO mapping.tag_document (tag_id, document_id, doc_number_raw, tag_name_raw, row_hash, sync_status, sync_timestamp)
                VALUES (:tid, :did, :dcr, :tnr, :h, 'New', :ts)
            """), doc_maps_to_insert)

        if doc_maps_to_update:
            conn.execute(text("""
                UPDATE mapping.tag_document SET sync_status='No Changes', sync_timestamp=:ts, row_hash=:h, 
                document_id=:did, doc_number_raw=:dcr, tag_name_raw=:tnr WHERE id=:id
            """), doc_maps_to_update)

        if sece_maps_to_insert:
            conn.execute(text("""
                INSERT INTO mapping.tag_sece (tag_id, sece_id, row_hash, sync_status, sync_timestamp) 
                VALUES (:tid, :sid, :h, 'New', :ts)
            """), sece_maps_to_insert)

        if sece_maps_to_update:
            conn.execute(text("UPDATE mapping.tag_sece SET sync_status='No Changes', sync_timestamp=:ts, row_hash=:h WHERE id=:id"), sece_maps_to_update)

        if history_to_insert:
            conn.execute(text("""
                INSERT INTO audit_core.tag_status_history
                    (tag_id, tag_name, source_id, sync_status, sync_timestamp, run_id, row_hash, snapshot)
                VALUES (:tid, :tn, :sid, :ss, :ts, :rid, :h, :snap)
            """), history_to_insert)

        # --- PHASE 5: CLEANUP (Within the same transaction) ---
        deleted_rows = conn.execute(text("""
            UPDATE project_core.tag SET sync_status = 'Deleted'
            WHERE sync_timestamp < :sync_date AND sync_status != 'Deleted'
            RETURNING id, tag_name, source_id
        """), {"sync_date": sync_time}).fetchall()
        if deleted_rows:
            conn.execute(text("""
                INSERT INTO audit_core.tag_status_history
                    (tag_id, tag_name, source_id, sync_status, sync_timestamp, run_id, row_hash, snapshot)
                VALUES (:tid, :tn, :sid, 'Deleted', :ts, :rid, NULL, NULL)
            """), [{"tid": r[0], "tn": r[1], "sid": r[2],
                    "ts": sync_time, "rid": run_id} for r in deleted_rows])
        for t in ["mapping.tag_document", "mapping.tag_sece"]:
            conn.execute(text(f"UPDATE {t} SET sync_status='Deleted' WHERE sync_timestamp < :sync_date AND sync_status != 'Deleted'"),
                         {"sync_date": sync_time})
        conn.execute(text("UPDATE project_core.tag SET object_status='Inactive' WHERE sync_status = 'Deleted' AND object_status != 'Inactive'"))

    # Final Audit (Separate transaction is fine)
    with engine.begin() as conn:
        count_updated = stats["Updated"] + stats["Extended"] + stats["Reduced"]
        logger.info(f"Updated breakdown — Updated: {stats['Updated']}, Extended: {stats['Extended']}, Reduced: {stats['Reduced']}")
        conn.execute(text("""
            UPDATE audit_core.sync_run_stats SET end_time=:et, count_created=:nc, count_updated=:nu, count_unchanged=:nch, count_errors=:ne WHERE run_id=:rid
        """), {"rid": run_id, "et": datetime.now(), "nc": stats["New"], "nu": count_updated, "nch": stats["No Changes"], "ne": stats["Errors"]})

@task(name="Resolve Parent-Child Hierarchy (Atomic)")
def build_hierarchy(override_file=None):
    logger = get_run_logger(); engine = create_engine(DB_URL)
    with engine.begin() as conn:
        logger.info("Executing atomic hierarchy resolution...")
        conn.execute(text("""
            UPDATE project_core.tag t
            SET parent_tag_id = p.id
            FROM project_core.tag p
            WHERE t.parent_tag_raw = p.tag_name
              AND (t.parent_tag_id IS NULL OR t.parent_tag_id != p.id)
              AND t.parent_tag_raw IS NOT NULL
              AND t.parent_tag_raw != ''
              AND t.parent_tag_raw != 'unset';
        """))
        conn.execute(text("""
            UPDATE project_core.tag t
            SET from_tag_id = f.id
            FROM project_core.tag f
            WHERE t.from_tag_raw = f.tag_name
              AND (t.from_tag_id IS NULL OR t.from_tag_id != f.id)
              AND t.from_tag_raw IS NOT NULL
              AND t.from_tag_raw != '';
        """))
        conn.execute(text("""
            UPDATE project_core.tag t
            SET to_tag_id = tt.id
            FROM project_core.tag tt
            WHERE t.to_tag_raw = tt.tag_name
              AND (t.to_tag_id IS NULL OR t.to_tag_id != tt.id)
              AND t.to_tag_raw IS NOT NULL
              AND t.to_tag_raw != '';
        """))

@flow(name="Tag Register Master Sync", log_prints=True)
def tag_sync_flow():
    rid = str(uuid.uuid4())
    sync_tags_task(rid)
    build_hierarchy()

if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent.parent)
    tag_sync_flow.serve(name="tag-sync-deployment")