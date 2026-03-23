"""Reverse ETL export flow: Master Equipment Register (EIS seq 004)."""

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

try:
    from tasks.common import load_config, get_db_engine_url
    from tasks.export_transforms import transform_equipment_register
    from tasks.export_pipeline import run_export_pipeline
except ImportError as e:
    print(f"[SKIP] {Path(__file__).name}: Could not import task modules. Details: {e}")
    sys.exit(0)

# Module-level config — same pattern as export_tag_register.py
config = load_config()
DB_URL = get_db_engine_url(config)
_EXPORT_DIR = config.get("storage", {}).get("export_dir", ".")

# ---------------------------------------------------------------------------
# SQL: Extract active equipment rows with all resolved FK references
# ---------------------------------------------------------------------------

_EQUIPMENT_REGISTER_SQL = """
/*
Purpose: Master Equipment Register full extract for EIS snapshot export (seq 004).
Gate:    t.object_status = 'Active' AND t.equip_no IS NOT NULL — equipment rows only.
Note:    STARTUP_DATE, PRICE, WARRANTY_END_DATE, TECHIDENTNO, ALIAS always exported as 'NA'.
         PART_OF = po_package.name via purchase_order.package_id.
Changes: 2026-03-10 — Initial implementation.
         2026-03-12 — PART_OF: pkg.name → pkg.code per EIS specification.
*/
SELECT
    t.equip_no                              AS equipment_number,
    pl.code                                 AS plant_code,
    t.tag_name                              AS tag_name,
    c.name                                  AS equipment_class_name,
    mco.name                                AS manufacturer_company_name,
    mp.name                                 AS model_part_name,
    t.serial_no                             AS manufacturer_serial_number,
    po.po_date                              AS purchase_date,
    vco.name                                AS vendor_company_name,
    t.install_date                          AS installation_date,
    'NA'                                    AS startup_date,
    'NA'                                    AS price,
    'NA'                                    AS warranty_end_date,
    COALESCE(pkg.code, '')                  AS part_of,
    'NA'                                    AS techidentno,
    'NA'                                    AS alias,
    t.description                           AS equipment_description,
    -- raw FK fields below: used by built-in FK validation rules, dropped by transform before CSV write
    t.model_part_raw                        AS model_part_raw,
    t.manufacturer_company_raw              AS manufacturer_company_raw,
    t.vendor_company_raw                    AS vendor_company_raw,
    t.plant_raw                             AS plant_raw,
    t.sync_status,
    t.sync_timestamp,
    t.tag_status,
    t.object_status
FROM project_core.tag t
-- Why LEFT JOIN: equipment row must not disappear from export due to NULL FK references
LEFT JOIN reference_core.plant          pl  ON pl.id  = t.plant_id
LEFT JOIN ontology_core.class           c   ON c.id   = t.class_id
LEFT JOIN reference_core.company        mco ON mco.id = t.manufacturer_id
LEFT JOIN reference_core.company        vco ON vco.id = t.vendor_id
LEFT JOIN reference_core.model_part     mp  ON mp.id  = t.model_id
LEFT JOIN reference_core.purchase_order po  ON po.id  = t.po_id
LEFT JOIN reference_core.po_package     pkg ON pkg.id = po.package_id
WHERE t.object_status = 'Active'
  AND t.equip_no IS NOT NULL
ORDER BY pl.code, t.tag_name
"""

_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-004-{revision}.CSV"


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="extract-equipment-register", retries=1, cache_policy=NO_CACHE)
def extract_equipment_register(engine: Engine) -> pd.DataFrame:
    """
    Run the Equipment Register SQL query and return a raw DataFrame.

    Args:
        engine: SQLAlchemy engine connected to engineering_core.

    Returns:
        DataFrame with all active equipment rows and resolved FK references.
    """
    logger = get_run_logger()
    # SELECT-only: no transaction context needed for read operations
    with engine.connect() as conn:
        df = pd.read_sql(text(_EQUIPMENT_REGISTER_SQL), conn)
    logger.info(f"Extracted {len(df)} active equipment rows")
    return df


# ---------------------------------------------------------------------------
# Prefect flow
# ---------------------------------------------------------------------------

@flow(name="export-equipment-register", log_prints=True)
def export_equipment_register_flow(
    doc_revision: str = "A01",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Master Equipment Register to EIS CSV snapshot (seq 004).

    Output file: JDAW-KVE-E-JA-6944-00001-004-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: object_status = 'Active' AND equip_no IS NOT NULL (SQL + Python second-defence).
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A01"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations" (total violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.

    Example:
        >>> export_equipment_register_flow(doc_revision="A01")
        {'exported': 850, 'violations': 0}
    """
    logger = get_run_logger()

    # Validate revision format before any DB work
    if not re.match(r"^[A-Z]\d{2}$", doc_revision):
        raise ValueError(
            f"doc_revision '{doc_revision}' is invalid. Expected format: [A-Z]\\d{{2}} (e.g. 'A01')."
        )

    engine = create_engine(DB_URL)
    output_path = Path(output_dir or _EXPORT_DIR) / _FILE_TEMPLATE.format(revision=doc_revision)

    return run_export_pipeline(
        engine=engine,
        scope="equipment",
        extract_fn=extract_equipment_register,
        transform_fn=transform_equipment_register,
        output_path=output_path,
        report_name="equipment_register",
        logger=logger,
    )


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    export_equipment_register_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/export_equipment_register_deploy.py:export_equipment_register_flow",
    ).deploy(
        name="export-equipment-register-deploy",
        work_pool_name="default-agent-pool",
    )
