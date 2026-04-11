"""Reverse ETL export flow: Tag Class Schema (EIS file 009, seq 307).

Exports tag classes actually in use in the project (>=1 active tag assigned)
together with their mapped properties from the CFIHOS ontology.

Output file: JDAW-KVE-E-JA-6944-00001-009-{rev}.CSV

Column schema (exact EIS order):
  CLASS_CODE, CLASS_NAME, CONCEPT, PROPERTY_CODE, PROPERTY_NAME,
  DATA_TYPE, IS_MANDATORY, VALID_VALUES, INSTANCE_COUNT

Files 010 and 011 are exported by dedicated flows:
  etl/flows/export_tag_properties_deploy.py       (file 010, Functional)
  etl/flows/export_equipment_properties_deploy.py (file 011, Physical)
"""

import re
import sys
from pathlib import Path

import pandas as pd
from prefect import flow, task, get_run_logger
from prefect.cache_policies import NO_CACHE
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

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

config = load_config()
DB_URL = get_db_engine_url(config)
_EXPORT_DIR = config.get("storage", {}).get("export_dir", ".")

_CLASS_SCHEMA_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-009-{revision}.CSV"

# ---------------------------------------------------------------------------
# SQL: Tag class schema (file 009)
# ---------------------------------------------------------------------------

_TAG_CLASS_SCHEMA_SQL = """
/*
Purpose : Tag class schema export for EIS file 009.
          One row per class x property mapping.
          CLASS_NAME: human-readable name from ontology_core.class (was TAG_CLASS_NAME).
          CONCEPT: sourced from ontology_core.class.concept (Functional / Physical /
                   Functional Physical).
          IS_MANDATORY: Y if mapping_presence = 'Mandatory', N otherwise.
          VALID_VALUES: picklist / regex from ontology_core.validation_rule.validation_value.
          INSTANCE_COUNT: active tags assigned to this class in project_core.tag.
Gate    : cp.mapping_status = 'Active'  (case-insensitive via UPPER())
          c.object_status  = 'Active'   (case-insensitive via UPPER())
          p.object_status  = 'Active'   (case-insensitive via UPPER())
Note    : ontology_core.class stores object_status as 'ACTIVE' (all-caps).
          UPPER() guards added 2026-04-11 to avoid touching source data.
Changes : 2026-04-11 — restored and extended (added CLASS_CODE, CONCEPT,
                        INSTANCE_COUNT; renamed TAG_CLASS_NAME -> CLASS_NAME).
          2026-04-11 — added UPPER() case-insensitive guards on all status filters.
*/
SELECT
    c.code                                          AS class_code,
    c.name                                          AS class_name,
    c.concept                                       AS concept,
    p.code                                          AS property_code,
    p.name                                          AS property_name,
    p.data_type                                     AS data_type,
    CASE WHEN cp.mapping_presence = 'Mandatory'
         THEN 'Y' ELSE 'N' END                      AS is_mandatory,
    COALESCE(vr.validation_value, '')               AS valid_values,
    COUNT(t.id) FILTER (
        WHERE UPPER(t.object_status) = 'ACTIVE'
    )                                               AS instance_count
FROM ontology_core.class_property cp
JOIN ontology_core.class   c  ON c.id  = cp.class_id
JOIN ontology_core.property p  ON p.id  = cp.property_id
LEFT JOIN ontology_core.validation_rule vr
       ON vr.id = p.validation_rule_id
LEFT JOIN project_core.tag t
       ON t.class_id = c.id
WHERE UPPER(cp.mapping_status) = 'ACTIVE'
  AND UPPER(c.object_status)   = 'ACTIVE'
  AND UPPER(p.object_status)   = 'ACTIVE'
GROUP BY c.code, c.name, c.concept,
         p.code, p.name, p.data_type,
         cp.mapping_presence,
         vr.validation_value
ORDER BY c.name, p.code
"""


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="extract-tag-class-schema", retries=1, cache_policy=NO_CACHE)
def extract_tag_class_schema(engine: Engine) -> pd.DataFrame:
    """Extract tag class schema rows for EIS file 009."""
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_TAG_CLASS_SCHEMA_SQL), conn)
    logger.info(f"Extracted {len(df)} class schema rows (file 009)")
    return df


# ---------------------------------------------------------------------------
# Prefect flow
# ---------------------------------------------------------------------------

@flow(name="export_tag_class_properties_data", log_prints=True)
def export_tag_class_properties_flow(
    doc_revision: str = "A37",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export tag class schema to EIS CSV snapshot (file 009, seq 307).

    Output file: JDAW-KVE-E-JA-6944-00001-009-{doc_revision}.CSV
    Scope:       File 009 only. Files 010/011 have dedicated flows.
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.

    Args:
        doc_revision: EIS revision code (e.g. "A37"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations".

    Example:
        >>> export_tag_class_properties_flow(doc_revision="A37")
        {'exported': 1850, 'violations': 0}
    """
    logger = get_run_logger()

    if not re.match(r"^[A-Z]\d{2}$", doc_revision):
        raise ValueError(
            f"doc_revision '{doc_revision}' is invalid. "
            f"Expected format: [A-Z]\\d{{2}} (e.g. 'A37')."
        )

    engine = create_engine(DB_URL)
    output_path = (
        Path(output_dir or _EXPORT_DIR)
        / _CLASS_SCHEMA_FILE_TEMPLATE.format(revision=doc_revision)
    )

    result = run_export_pipeline(
        engine=engine,
        scope="common",
        extract_fn=extract_tag_class_schema,
        transform_fn=transform_tag_class_properties,
        output_path=output_path,
        report_name="tag_class_schema_009",
        logger=logger,
    )

    logger.info(
        f"Export complete: 009={result['exported']} rows, "
        f"violations={result['violations']}"
    )

    return {
        "exported": result["exported"],
        "violations": result["violations"],
    }


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    export_tag_class_properties_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/export_tag_class_properties_deploy.py:export_tag_class_properties_flow",
    ).deploy(
        name="export_tag_class_properties_data_deploy",
        work_pool_name="default-agent-pool",
    )
