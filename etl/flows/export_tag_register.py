"""Reverse ETL export flow: Master Tag Register (EIS seq 003)."""

import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
from prefect import flow, task, get_run_logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Setup import path so tasks.* resolves from etl/
current_dir = Path(__file__).resolve().parent
script_root = current_dir.parent
if str(script_root) not in sys.path:
    sys.path.append(str(script_root))

from tasks.common import load_config, get_db_engine_url
from tasks.export_transforms import transform_tag_register, write_csv

# ---------------------------------------------------------------------------
# SQL: Extract active tags with all resolved FK references
# ---------------------------------------------------------------------------

_TAG_REGISTER_SQL = """
/*
Purpose: Master Tag Register full extract for EIS snapshot export (seq 003).
Gate:    t.object_status = 'Active' — primary indexed filter.
Note:    SAFETY_CRITICAL_ITEM_GROUP aggregated via correlated subquery
         (one tag may map to N active SECEs).
Changes: 2026-03-10 — Initial implementation.
*/
SELECT
    pl.code                                     AS PLANT_CODE,
    t.tag_name                                  AS TAG_NAME,
    COALESCE(pt.tag_name, '')                   AS PARENT_TAG_NAME,
    a.code                                      AS AREA_CODE,
    u.code                                      AS PROCESS_UNIT_CODE,
    c.name                                      AS TAG_CLASS_NAME,
    t.tag_status                                AS TAG_STATUS,
    po.code                                     AS REQUISITION_CODE,
    dco.name                                    AS DESIGNED_BY_COMPANY_NAME,
    dco.name                                    AS COMPANY_NAME,
    po.code                                     AS PO_CODE,
    t.production_critical_item                  AS PRODUCTION_CRITICAL_ITEM,
    t.safety_critical_item                      AS SAFETY_CRITICAL_ITEM,
    -- Why correlated subquery: one tag may have multiple active SECE mappings
    (
        SELECT STRING_AGG(s.code, ' ' ORDER BY s.code)
        FROM mapping.tag_sece ts2
        JOIN reference_core.sece s ON s.id = ts2.sece_id
        WHERE ts2.tag_id = t.id
          AND ts2.mapping_status = 'Active'
    )                                           AS SAFETY_CRITICAL_ITEM_GROUP,
    t.safety_critical_item_reason_awarded       AS SAFETY_CRITICAL_ITEM_REASON_AWARDED,
    t.description                               AS TAG_DESCRIPTION,
    t.sync_status,
    t.sync_timestamp,
    t.object_status
FROM project_core.tag t
-- Why LEFT JOIN: tag must not disappear from export due to NULL FK references
LEFT JOIN reference_core.plant          pl  ON pl.id  = t.plant_id
LEFT JOIN reference_core.area           a   ON a.id   = t.area_id
LEFT JOIN reference_core.process_unit   u   ON u.id   = t.process_unit_id
LEFT JOIN ontology_core.class           c   ON c.id   = t.class_id
LEFT JOIN project_core.tag              pt  ON pt.id  = t.parent_tag_id
LEFT JOIN reference_core.company        dco ON dco.id = t.design_company_id
LEFT JOIN reference_core.purchase_order po  ON po.id  = t.po_id
WHERE t.object_status = 'Active'
ORDER BY pl.code, t.tag_name
"""

_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-003-{revision}.CSV"


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="extract-tag-register", retries=1)
def extract_tag_register(engine: Engine) -> pd.DataFrame:
    """
    Run the Tag Register SQL query and return a raw DataFrame.

    Args:
        engine: SQLAlchemy engine connected to engineering_core.

    Returns:
        DataFrame with all active tags and resolved FK references.
    """
    logger = get_run_logger()
    # SELECT-only: no transaction context needed for read operations
    with engine.connect() as conn:
        df = pd.read_sql(text(_TAG_REGISTER_SQL), conn)
    logger.info(f"Extracted {len(df)} active tag rows")
    return df


def _log_audit_start(engine: Engine, run_id: str, source_file: str) -> None:
    """Insert audit start record into sync_run_stats."""
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO audit_core.sync_run_stats
                (run_id, target_table, start_time, source_file)
            VALUES (:rid, :tbl, :st, :sf)
        """), {
            "rid": run_id,
            "tbl": "project_core.tag",
            "st": datetime.now(),
            "sf": source_file,
        })


def _log_audit_end(engine: Engine, run_id: str, row_count: int) -> None:
    """Update audit record with end time and exported row count."""
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE audit_core.sync_run_stats
               SET end_time       = :et,
                   count_unchanged = :rc
             WHERE run_id = :rid
        """), {"et": datetime.now(), "rc": row_count, "rid": run_id})


# ---------------------------------------------------------------------------
# Prefect flow
# ---------------------------------------------------------------------------

@flow(name="export-tag-register", log_prints=True)
def export_tag_register_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
    config_path: str = "config/db_config.yaml",
) -> dict[str, int]:
    """
    Export Master Tag Register to EIS CSV snapshot (seq 003).

    Output file: JDAW-KVE-E-JA-6944-00001-003-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: object_status = 'Active' (SQL + Python second-defence).
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A35"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.
        config_path: Path to db_config.yaml (relative to working directory).

    Returns:
        dict with key "exported" = number of rows written to CSV.

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.

    Example:
        >>> export_tag_register_flow(doc_revision="A35")
        {'exported': 1500}
    """
    logger = get_run_logger()

    # Validate revision format before any DB work
    if not re.match(r"^[A-Z]\d{2}$", doc_revision):
        raise ValueError(
            f"doc_revision '{doc_revision}' is invalid. Expected format: [A-Z]\\d{{2}} (e.g. 'A35')."
        )

    config = load_config(config_path)
    engine = create_engine(get_db_engine_url(config))

    resolved_dir = output_dir or config.get("storage", {}).get("export_dir", ".")
    output_path = Path(resolved_dir) / _FILE_TEMPLATE.format(revision=doc_revision)

    run_id = str(uuid.uuid4())
    logger.info(f"Starting export run {run_id} → {output_path}")
    _log_audit_start(engine, run_id, str(output_path))

    raw_df = extract_tag_register(engine)
    clean_df = transform_tag_register(raw_df)

    row_count = write_csv(clean_df, output_path)
    logger.info(f"Exported {row_count} rows to {output_path}")

    _log_audit_end(engine, run_id, row_count)
    return {"exported": row_count}


if __name__ == "__main__":
    import os
    os.chdir(Path(__file__).resolve().parent.parent)
    export_tag_register_flow.serve(name="export-tag-register-deployment")
