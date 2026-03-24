"""Reverse ETL export flow: Tag Class Properties (EIS seq 307)."""

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
    from tasks.export_transforms import transform_tag_class_properties
    from tasks.export_pipeline import run_export_pipeline
except ImportError as e:
    print(f"[SKIP] {Path(__file__).name}: Could not import task modules. Details: {e}")
    sys.exit(0)

# Module-level config — same pattern as other export flows
config = load_config()
DB_URL = get_db_engine_url(config)
_EXPORT_DIR = config.get("storage", {}).get("export_dir", ".")

# ---------------------------------------------------------------------------
# SQL: Extract tag class property schema (Functional concept only)
# ---------------------------------------------------------------------------

_TAG_CLASS_PROPERTIES_SQL = """
/*
Purpose: Tag Class Properties schema export for EIS (seq 307).
Gate:    cp.mapping_status = 'Active'
         cp.mapping_concept ILIKE '%Functional%'  — Tag classes only (excludes Physical-only)
         c.object_status ILIKE 'Active'            — stored as 'ACTIVE' (uppercase) in DB
         p.object_status = 'Active'
Note:    mapping_presence is NULL in many rows — CASE maps NULL to 'N' (not mandatory).
         validation_rule may be NULL — COALESCE returns empty string.
Changes: 2026-03-13 — Initial implementation.
*/
SELECT
    c.name                              AS TAG_CLASS_NAME,
    p.code                              AS PROPERTY_CODE,
    p.name                              AS PROPERTY_NAME,
    COALESCE(p.data_type, '')           AS DATA_TYPE,
    CASE WHEN cp.mapping_presence = 'Mandatory' THEN 'Y' ELSE 'N' END AS IS_MANDATORY,
    COALESCE(vr.validation_value, '')   AS VALID_VALUES
FROM ontology_core.class_property cp
-- Why INNER JOIN: rows without a valid class or property are ontology integrity errors
JOIN ontology_core.class c ON c.id = cp.class_id
JOIN ontology_core.property p ON p.id = cp.property_id
-- Why LEFT JOIN: not all properties have a picklist — NULL valid_values is expected
LEFT JOIN ontology_core.validation_rule vr ON vr.id = p.validation_rule_id
WHERE cp.mapping_status = 'Active'
  AND cp.mapping_concept ILIKE '%Functional%'
  AND c.object_status ILIKE 'Active'
  AND p.object_status = 'Active'
ORDER BY c.name, p.code
"""

_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-009-{revision}.CSV"


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="extract-tag-class-properties", retries=1, cache_policy=NO_CACHE)
def extract_tag_class_properties(engine: Engine) -> pd.DataFrame:
    """
    Run the Tag Class Properties SQL query and return a raw DataFrame.

    Filters to Functional mapping_concept only — Physical-only class properties
    (equipment schema) are excluded from seq 307.

    Args:
        engine: SQLAlchemy engine connected to engineering_core.

    Returns:
        DataFrame with active tag class property schema rows.
    """
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_TAG_CLASS_PROPERTIES_SQL), conn)
    logger.info(f"Extracted {len(df)} active tag class property rows (Functional concept)")
    return df


# ---------------------------------------------------------------------------
# Prefect flow
# ---------------------------------------------------------------------------

@flow(name="export_tag_class_properties_data", log_prints=True)
def export_tag_class_properties_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Tag Class Properties to EIS CSV snapshot (seq 307).

    Output file: JDAW-KVE-E-JA-6944-00001-009-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: mapping_status = 'Active', mapping_concept ILIKE '%Functional%',
                 class.object_status ILIKE 'Active' (stored as 'ACTIVE' in DB).
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A35"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations" (total violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.

    Example:
        >>> export_tag_class_properties_flow(doc_revision="A35")
        {'exported': 2230, 'violations': 0}
    """
    logger = get_run_logger()

    if not re.match(r"^[A-Z]\d{2}$", doc_revision):
        raise ValueError(
            f"doc_revision '{doc_revision}' is invalid. Expected format: [A-Z]\\d{{2}} (e.g. 'A35')."
        )

    engine = create_engine(DB_URL)
    output_path = Path(output_dir or _EXPORT_DIR) / _FILE_TEMPLATE.format(revision=doc_revision)

    return run_export_pipeline(
        engine=engine,
        scope="tag_class_property",
        extract_fn=extract_tag_class_properties,
        transform_fn=transform_tag_class_properties,
        output_path=output_path,
        report_name="tag_class_properties",
        logger=logger,
    )


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    export_tag_class_properties_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/export_tag_class_properties_deploy.py:export_tag_class_properties_flow",
    ).deploy(
        name="export_tag_class_properties_data_deploy",
        work_pool_name="default-agent-pool",
    )
