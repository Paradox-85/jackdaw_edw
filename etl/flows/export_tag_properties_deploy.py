"""Reverse ETL export flow: Tag Instance Property Values (EIS file 010, seq 303).

Column schema (exact EIS order):
  PLANT_CODE, TAG_NAME, PROPERTY_NAME, PROPERTY_VALUE, PROPERTY_VALUE_UOM
"""

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
    from tasks.export_transforms import transform_tag_instance_properties
    from tasks.export_pipeline import run_export_pipeline, _load_uom_lookup
except ImportError as e:
    print(f"[SKIP] {Path(__file__).name}: Could not import task modules. Details: {e}")
    sys.exit(0)

# Module-level config — same pattern as other export flows
config = load_config()
DB_URL = get_db_engine_url(config)
_EXPORT_DIR = config.get("storage", {}).get("export_dir", ".")

# ---------------------------------------------------------------------------
# SQL: Extract active tag property values with Functional mapping_concept
# ---------------------------------------------------------------------------

_TAG_PROPERTIES_SQL = """
/*
Purpose: Tag Property Values full extract for EIS snapshot export (seq 303).
Gate:    pv.object_status = 'Active'
         AND cp.mapping_concept ILIKE '%Functional%'
         AND cp.mapping_concept NOT ILIKE '%common%'
Routing: Functional concept → seq 303 (this file, -010-)
         Physical concept   → seq 301 (export_equipment_properties.py, -011-)
         common concept     → excluded (already in tag/equipment registers)
Note:    ILIKE '%...%' used because mapping_concept may be composite,
         e.g. 'Functional Physical'.
Changes: 2026-03-13 — Initial implementation.
         2026-04-09 — Added uom_alias join for symbol_ascii resolution.
*/
-- BUG-6: DISTINCT eliminates duplicate rows that arise when a property_value
-- row is linked to multiple class_property entries with Functional mapping_concept.
SELECT DISTINCT
    pl.code                         AS PLANT_CODE,
    t.tag_name                      AS TAG_NAME,
    p.name                          AS PROPERTY_NAME,
    pv.property_value               AS PROPERTY_VALUE,
    COALESCE(u.symbol_ascii, u.symbol, pv.property_uom_raw) AS PROPERTY_VALUE_UOM,
    -- internal fields for validation rules (dropped by transform before CSV write)
    pv.id                           AS object_id,
    t.tag_name                      AS object_name,
    pv.object_status
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
-- Resolve property_uom_raw to canonical symbol_ascii via uom_alias
LEFT JOIN ontology_core.uom_alias ua
    ON LOWER(TRIM(pv.property_uom_raw)) = ua.alias_lower
LEFT JOIN ontology_core.uom u
    ON ua.uom_id = u.id
WHERE pv.object_status = 'Active'
  AND cp.mapping_concept ILIKE '%Functional%'
  AND cp.mapping_concept NOT ILIKE '%common%'
ORDER BY pl.code, t.tag_name, p.name
"""

_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-010-{revision}.CSV"


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="extract-tag-properties", retries=1, cache_policy=NO_CACHE)
def extract_tag_properties(engine: Engine) -> pd.DataFrame:
    """
    Run the Tag Property Values SQL query and return a raw DataFrame.

    Filters to Functional mapping_concept only — Physical rows are handled
    by export_equipment_properties.py, common rows are excluded from both.

    Args:
        engine: SQLAlchemy engine connected to engineering_core.

    Returns:
        DataFrame with active tag property value rows (Functional concept).
    """
    logger = get_run_logger()
    # SELECT-only: no transaction context needed for read operations
    with engine.connect() as conn:
        df = pd.read_sql(text(_TAG_PROPERTIES_SQL), conn)
    logger.info(f"Extracted {len(df)} active tag property value rows (Functional)")
    return df


# ---------------------------------------------------------------------------
# Prefect flow
# ---------------------------------------------------------------------------

@flow(name="export_tag_properties_data", log_prints=True)
def export_tag_properties_flow(
    doc_revision: str = "A01",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Tag Property Values to EIS CSV snapshot (seq 303).

    Output file: JDAW-KVE-E-JA-6944-00001-010-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: pv.object_status = 'Active' AND mapping_concept ILIKE '%Functional%'
                 AND NOT ILIKE '%common%' (SQL + Python second-defence).
    Routing:     Functional concept only. Physical → export_equipment_properties_flow.
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A01"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations" (total violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.

    Example:
        >>> export_tag_properties_flow(doc_revision="A01")
        {'exported': 45230, 'violations': 0}
    """
    logger = get_run_logger()

    # Validate revision format before any DB work
    if not re.match(r"^[A-Z]\d{2}$", doc_revision):
        raise ValueError(
            f"doc_revision '{doc_revision}' is invalid. Expected format: [A-Z]\\d{{2}} (e.g. 'A01')."
        )

    engine = create_engine(DB_URL)

    # Load UoM lookup for value/UoM splitting (safe if table doesn't exist yet)
    uom_lookup = _load_uom_lookup(engine)

    output_path = Path(output_dir or _EXPORT_DIR) / _FILE_TEMPLATE.format(revision=doc_revision)

    return run_export_pipeline(
        engine=engine,
        scope="tag_property",
        extract_fn=extract_tag_properties,
        transform_fn=lambda df: transform_tag_instance_properties(df, uom_lookup),
        output_path=output_path,
        report_name="tag_properties",
        logger=logger,
    )


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    export_tag_properties_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/export_tag_properties_deploy.py:export_tag_properties_flow",
    ).deploy(
        name="export_tag_properties_data_deploy",
        work_pool_name="default-agent-pool",
    )
