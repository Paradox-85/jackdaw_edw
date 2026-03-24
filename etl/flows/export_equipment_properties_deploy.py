"""Reverse ETL export flow: Equipment Property Values (EIS seq 301)."""

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
    from tasks.export_transforms import transform_equipment_properties
    from tasks.export_pipeline import run_export_pipeline
except ImportError as e:
    print(f"[SKIP] {Path(__file__).name}: Could not import task modules. Details: {e}")
    sys.exit(0)

# Module-level config — same pattern as other export flows
config = load_config()
DB_URL = get_db_engine_url(config)
_EXPORT_DIR = config.get("storage", {}).get("export_dir", ".")

# ---------------------------------------------------------------------------
# SQL: Extract active equipment property values with Physical mapping_concept
# ---------------------------------------------------------------------------

_EQUIPMENT_PROPERTIES_SQL = """
/*
Purpose: Equipment Property Values full extract for EIS snapshot export (seq 301).
Gate:    pv.object_status = 'Active'
         AND cp.mapping_concept ILIKE '%Physical%'
         AND cp.mapping_concept NOT ILIKE '%common%'
Routing: Physical concept   → seq 301 (this file, -011-)
         Functional concept → seq 303 (export_tag_properties.py, -010-)
         common concept     → excluded (already in tag/equipment registers)
Note:    ILIKE '%...%' used because mapping_concept may be composite,
         e.g. 'Functional Physical'. Such rows appear in BOTH exports.
Changes: 2026-03-13 — Initial implementation.
*/
SELECT
    pl.code                         AS PLANT_CODE,
    t.tag_name                      AS TAG_NAME,
    p.code                          AS PROPERTY_CODE,
    pv.property_value               AS PROPERTY_VALUE,
    pv.property_uom_raw             AS UNIT,
    -- internal fields for validation rules (dropped by transform before CSV write)
    pv.id                           AS object_id,
    t.tag_name                      AS object_name,
    cp.mapping_concept              AS mapping_concept_raw,
    pv.object_status,
    pv.sync_status,
    pv.sync_timestamp
FROM project_core.property_value pv
-- Why INNER JOIN on tag and class_property: rows without a valid tag or mapping
-- are data integrity errors — they must not silently appear in the export
JOIN project_core.tag t
    ON pv.tag_id = t.id
JOIN ontology_core.class_property cp
    ON pv.mapping_id = cp.id
JOIN ontology_core.property p
    ON pv.property_id = p.id
-- Why LEFT JOIN on plant: tag must not disappear due to missing plant FK
LEFT JOIN reference_core.plant pl
    ON t.plant_id = pl.id
WHERE pv.object_status = 'Active'
  AND cp.mapping_concept ILIKE '%Physical%'
  AND cp.mapping_concept NOT ILIKE '%common%'
ORDER BY pl.code, t.tag_name, p.code
"""

_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-011-{revision}.CSV"


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="extract-equipment-properties", retries=1, cache_policy=NO_CACHE)
def extract_equipment_properties(engine: Engine) -> pd.DataFrame:
    """
    Run the Equipment Property Values SQL query and return a raw DataFrame.

    Filters to Physical mapping_concept only — Functional rows are handled
    by export_tag_properties.py, common rows are excluded from both.

    Args:
        engine: SQLAlchemy engine connected to engineering_core.

    Returns:
        DataFrame with active equipment property value rows (Physical concept).
    """
    logger = get_run_logger()
    # SELECT-only: no transaction context needed for read operations
    with engine.connect() as conn:
        df = pd.read_sql(text(_EQUIPMENT_PROPERTIES_SQL), conn)
    logger.info(f"Extracted {len(df)} active equipment property value rows (Physical)")
    return df


# ---------------------------------------------------------------------------
# Prefect flow
# ---------------------------------------------------------------------------

@flow(name="export_equipment_properties_data", log_prints=True)
def export_equipment_properties_flow(
    doc_revision: str = "A01",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Equipment Property Values to EIS CSV snapshot (seq 301).

    Output file: JDAW-KVE-E-JA-6944-00001-011-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: pv.object_status = 'Active' AND mapping_concept ILIKE '%Physical%'
                 AND NOT ILIKE '%common%' (SQL + Python second-defence).
    Routing:     Physical concept only. Functional → export_tag_properties_flow.
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A01"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations" (total violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.

    Example:
        >>> export_equipment_properties_flow(doc_revision="A01")
        {'exported': 12400, 'violations': 0}
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
        scope="equipment_property",
        extract_fn=extract_equipment_properties,
        transform_fn=transform_equipment_properties,
        output_path=output_path,
        report_name="equipment_properties",
        logger=logger,
    )


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    export_equipment_properties_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/export_equipment_properties_deploy.py:export_equipment_properties_flow",
    ).deploy(
        name="export_equipment_properties_data_deploy",
        work_pool_name="default-agent-pool",
    )
