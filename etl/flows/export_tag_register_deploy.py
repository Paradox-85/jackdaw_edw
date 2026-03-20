"""Reverse ETL export flow: Master Tag Register (EIS seq 003)."""

import re
import sys
from pathlib import Path

import pandas as pd
from prefect import flow, task, get_run_logger
from prefect.cache_policies import NO_CACHE
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Setup import path so tasks.* resolves from etl/
current_dir = Path(__file__).resolve().parent
script_root = current_dir.parent
if str(script_root) not in sys.path:
    sys.path.append(str(script_root))

from tasks.common import load_config, get_db_engine_url
from tasks.export_transforms import transform_tag_register
from tasks.export_pipeline import run_export_pipeline

# Module-level config — same pattern as sync_tag_data.py and other flows
config = load_config()
DB_URL = get_db_engine_url(config)
_EXPORT_DIR = config.get("storage", {}).get("export_dir", ".")

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
    COALESCE(art.name, art.code)                AS REQUISITION_CODE,
    dco.name                                    AS DESIGNED_BY_COMPANY_NAME,
    COALESCE(ico.name, '')                      AS COMPANY_NAME,
    COALESCE(po.name, po.code)                  AS PO_CODE,
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
    -- raw FK fields below: used by built-in FK validation rules, dropped by transform before CSV write
    t.area_code_raw                             AS area_code_raw,
    t.tag_class_raw                             AS tag_class_raw,
    t.process_unit_raw                          AS process_unit_raw,
    t.plant_raw                                 AS plant_raw,
    t.design_company_name_raw                   AS design_company_name_raw,
    t.po_code_raw                               AS po_code_raw,
    t.article_code_raw                          AS article_code_raw,
    t.parent_tag_raw                            AS parent_tag_raw,
    t.discipline_code_raw                       AS discipline_code_raw,
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
LEFT JOIN reference_core.article        art ON art.id = t.article_id
LEFT JOIN reference_core.company        ico ON ico.id = po.issuer_id
WHERE t.object_status = 'Active'
ORDER BY pl.code, t.tag_name
"""

_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-003-{revision}.CSV"


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="extract-tag-register", retries=1, cache_policy=NO_CACHE)
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


# ---------------------------------------------------------------------------
# Prefect flow
# ---------------------------------------------------------------------------

@flow(name="export-tag-register", log_prints=True)
def export_tag_register_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
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

    Returns:
        dict with keys "exported" (rows written) and "violations" (total violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.

    Example:
        >>> export_tag_register_flow(doc_revision="A35")
        {'exported': 1500, 'violations': 0}
    """
    logger = get_run_logger()

    # Validate revision format before any DB work
    if not re.match(r"^[A-Z]\d{2}$", doc_revision):
        raise ValueError(
            f"doc_revision '{doc_revision}' is invalid. Expected format: [A-Z]\\d{{2}} (e.g. 'A35')."
        )

    engine = create_engine(DB_URL)
    output_path = Path(output_dir or _EXPORT_DIR) / _FILE_TEMPLATE.format(revision=doc_revision)

    return run_export_pipeline(
        engine=engine,
        scope="tag",
        extract_fn=extract_tag_register,
        transform_fn=transform_tag_register,
        output_path=output_path,
        report_name="tag_register",
        logger=logger,
    )


if __name__ == "__main__":
    import os
    os.chdir(Path(__file__).resolve().parent.parent)
    export_tag_register_flow.serve(name="export-tag-register-deployment")
