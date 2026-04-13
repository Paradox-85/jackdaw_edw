"""Stub container for schema/class-property mapping exports (file 009 / 009b).

Exports tag classes and equipment classes actually in use in the project
(>=1 active tag assigned) together with their mapped properties from the
CFIHOS ontology.  Two outputs — Functional (file 009) and Physical (file 009b).

Output files:
  JDAW-KVE-E-JA-6944-00001-009-{rev}.CSV   — Functional tag classes  (deployed when ready)
  JDAW-KVE-E-JA-6944-00001-009b-{rev}.CSV  — Physical equipment classes (placeholder)

Column schema:
  file 009  : TAG_CLASS_NAME, TAG_PROPERTY_NAME
  file 009b : EQUIPMENT_CLASS_NAME, EQUIPMENT_PROPERTY_NAME

Files 010 and 011 are exported by dedicated flows:
  etl/flows/export_tag_properties_deploy.py       (file 010, Functional)
  etl/flows/export_equipment_properties_deploy.py (file 011, Physical)

Not deployed to Prefect — stub for future use.
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
    from tasks.export_transforms import transform_tag_class_schema, transform_equipment_class_schema
    from tasks.export_pipeline import run_export_pipeline
except ImportError as e:
    print(f"[SKIP] {Path(__file__).name}: Could not import task modules. Details: {e}")
    sys.exit(0)

config = load_config()
DB_URL = get_db_engine_url(config)
_EXPORT_DIR = config.get("storage", {}).get("export_dir", ".")

_TAG_CLASS_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-009-{revision}.CSV"
_EQUIP_CLASS_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-009b-{revision}.CSV"

# ---------------------------------------------------------------------------
# SQL: Tag class schema — Functional classes only (file 009)
# ---------------------------------------------------------------------------

_TAG_CLASS_SCHEMA_SQL = """
/*
Purpose : Tag class schema export for EIS file 009.
          One row per Functional class x property mapping.
          Only classes with at least one active tag in project_core.tag are included.
          Output columns: TAG_CLASS_NAME, TAG_PROPERTY_NAME.
Gate    : cp.mapping_status = 'Active'  (case-insensitive via UPPER())
          c.object_status  = 'Active'   (case-insensitive via UPPER())
          p.object_status  = 'Active'   (case-insensitive via UPPER())
          cp.mapping_concept LIKE '%FUNCTIONAL%' (case-insensitive via UPPER())
Note    : ontology_core.class stores object_status as 'ACTIVE' (all-caps).
          UPPER() guards match existing pattern in codebase.
Changes : 2026-04-11 — restored and extended (added CLASS_CODE, CONCEPT,
                        INSTANCE_COUNT; renamed TAG_CLASS_NAME -> CLASS_NAME).
          2026-04-11 — added UPPER() case-insensitive guards on all status filters.
          2026-04-13 — columns reduced to TAG_CLASS_NAME/TAG_PROPERTY_NAME;
                        added Functional mapping_concept filter and HAVING active-tag guard.
*/
SELECT
    c.name                                          AS TAG_CLASS_NAME,
    p.name                                          AS TAG_PROPERTY_NAME
FROM ontology_core.class_property cp
JOIN ontology_core.class   c  ON c.id  = cp.class_id
JOIN ontology_core.property p  ON p.id  = cp.property_id
LEFT JOIN project_core.tag t
       ON t.class_id = c.id
WHERE UPPER(cp.mapping_status)  = 'ACTIVE'
  AND UPPER(c.object_status)    = 'ACTIVE'
  AND UPPER(p.object_status)    = 'ACTIVE'
  AND UPPER(cp.mapping_concept) LIKE '%FUNCTIONAL%'
GROUP BY c.name, p.name
HAVING COUNT(t.id) FILTER (WHERE UPPER(t.object_status) = 'ACTIVE') > 0
ORDER BY c.name, p.name
"""

# ---------------------------------------------------------------------------
# SQL: Equipment class schema — Physical classes only (file 009b, placeholder)
# ---------------------------------------------------------------------------

_EQUIP_CLASS_SCHEMA_SQL = """
/*
Purpose : Equipment class schema export for EIS file 009b (placeholder — no EIS seq assigned).
          One row per Physical class x property mapping.
          Only classes with at least one active tag in project_core.tag are included.
          Output columns: EQUIPMENT_CLASS_NAME, EQUIPMENT_PROPERTY_NAME.
Gate    : cp.mapping_status = 'Active'  (case-insensitive via UPPER())
          c.object_status  = 'Active'   (case-insensitive via UPPER())
          p.object_status  = 'Active'   (case-insensitive via UPPER())
          cp.mapping_concept LIKE '%PHYSICAL%' (case-insensitive via UPPER())
Note    : Mirror of _TAG_CLASS_SCHEMA_SQL with Physical filter.
          UPPER() guards match existing pattern in codebase.
Changes : 2026-04-13 — Initial implementation as Physical mirror of file 009.
*/
SELECT
    c.name                                          AS EQUIPMENT_CLASS_NAME,
    p.name                                          AS EQUIPMENT_PROPERTY_NAME
FROM ontology_core.class_property cp
JOIN ontology_core.class   c  ON c.id  = cp.class_id
JOIN ontology_core.property p  ON p.id  = cp.property_id
LEFT JOIN project_core.tag t
       ON t.class_id = c.id
WHERE UPPER(cp.mapping_status)  = 'ACTIVE'
  AND UPPER(c.object_status)    = 'ACTIVE'
  AND UPPER(p.object_status)    = 'ACTIVE'
  AND UPPER(cp.mapping_concept) LIKE '%PHYSICAL%'
GROUP BY c.name, p.name
HAVING COUNT(t.id) FILTER (WHERE UPPER(t.object_status) = 'ACTIVE') > 0
ORDER BY c.name, p.name
"""


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="extract-tag-class-schema", retries=1, cache_policy=NO_CACHE)
def extract_tag_class_schema(engine: Engine) -> pd.DataFrame:
    """Extract Functional tag class schema rows for EIS file 009."""
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_TAG_CLASS_SCHEMA_SQL), conn)
    logger.info(f"Extracted {len(df)} Functional class schema rows (file 009)")
    return df


@task(name="extract-equipment-class-schema", retries=1, cache_policy=NO_CACHE)
def extract_equipment_class_schema(engine: Engine) -> pd.DataFrame:
    """Extract Physical equipment class schema rows for EIS file 009b."""
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_EQUIP_CLASS_SCHEMA_SQL), conn)
    logger.info(f"Extracted {len(df)} Physical class schema rows (file 009b)")
    return df


# ---------------------------------------------------------------------------
# Prefect flows
# ---------------------------------------------------------------------------

@flow(name="export_tag_class_properties_data", log_prints=True)
def export_tag_class_properties_flow(
    doc_revision: str = "A37",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Functional tag class schema to EIS CSV snapshot (file 009).

    Output file: JDAW-KVE-E-JA-6944-00001-009-{doc_revision}.CSV
    Scope:       Functional tag classes with >=1 active tag in project.
    Columns:     TAG_CLASS_NAME, TAG_PROPERTY_NAME.
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
        / _TAG_CLASS_FILE_TEMPLATE.format(revision=doc_revision)
    )

    result = run_export_pipeline(
        engine=engine,
        scope="common",
        extract_fn=extract_tag_class_schema,
        transform_fn=transform_tag_class_schema,
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


@flow(name="export_equipment_class_properties_data", log_prints=True)
def export_equipment_class_properties_flow(
    doc_revision: str = "A37",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Physical equipment class schema to EIS CSV snapshot (file 009b).

    Output file: JDAW-KVE-E-JA-6944-00001-009b-{doc_revision}.CSV
    Scope:       Physical equipment classes with >=1 active tag in project.
    Columns:     EQUIPMENT_CLASS_NAME, EQUIPMENT_PROPERTY_NAME.
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Status:      Stub — not deployed to Prefect.

    Args:
        doc_revision: EIS revision code (e.g. "A37"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations".

    Example:
        >>> export_equipment_class_properties_flow(doc_revision="A37")
        {'exported': 920, 'violations': 0}
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
        / _EQUIP_CLASS_FILE_TEMPLATE.format(revision=doc_revision)
    )

    result = run_export_pipeline(
        engine=engine,
        scope="common",
        extract_fn=extract_equipment_class_schema,
        transform_fn=transform_equipment_class_schema,
        output_path=output_path,
        report_name="equip_class_schema_009b",
        logger=logger,
    )

    logger.info(
        f"Export complete: 009b={result['exported']} rows, "
        f"violations={result['violations']}"
    )

    return {
        "exported": result["exported"],
        "violations": result["violations"],
    }


# Not deployed to Prefect — stub for future use.
# if __name__ == "__main__":
#     _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
#     export_tag_class_properties_flow.from_source(
#         source=str(_REPO_ROOT),
#         entrypoint="etl/flows/export_schema_deploy.py:export_tag_class_properties_flow",
#     ).deploy(
#         name="export_tag_class_properties_data_deploy",
#         work_pool_name="default-agent-pool",
#     )
