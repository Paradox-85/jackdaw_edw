"""Reverse ETL export flow: Tag Instance Property Values (EIS files 010 + 011).

Replaces the previous Tag Class Properties schema export (seq 307).
Exports tag instance property values for:
  - File 010: Functional concept tags  (JDAW-KVE-E-JA-6944-00001-010-{rev}.CSV)
  - File 011: Physical concept tags    (JDAW-KVE-E-JA-6944-00001-011-{rev}.CSV)

Both files share the same 5-column schema (exact EIS order):
  PLANT_CODE, TAG_NAME, PROPERTY_NAME, PROPERTY_VALUE, PROPERTY_VALUE_UOM

PROPERTY_NAME  = human-readable name (ontology_core.property.name), NOT p.code
PROPERTY_VALUE_UOM = uom.symbol (mixed-case preserved, e.g. "degC", "kPa(g)", "mm2").
                     Do NOT uppercase this column.
"""

import functools
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
    from tasks.export_transforms import transform_tag_instance_properties
    from tasks.export_pipeline import run_export_pipeline, _load_uom_lookup
except ImportError as e:
    print(f"[SKIP] {Path(__file__).name}: Could not import task modules. Details: {e}")
    sys.exit(0)

config = load_config()
DB_URL = get_db_engine_url(config)
_EXPORT_DIR = config.get("storage", {}).get("export_dir", ".")

# ---------------------------------------------------------------------------
# SQL: Functional concept tag instance property values (file 010)
# ---------------------------------------------------------------------------

_TAG_PROPERTY_VALUES_SQL = """
/*
Purpose : Tag instance property values for EIS file 010.
Gate    : t.object_status = 'Active'
          cp.mapping_concept ILIKE '%Functional%'
          pv.property_value IS NOT NULL AND pv.property_value <> ''
          Rows where value = NULL or '' excluded at SQL level.
          Rows where value = 'TBC' are INCLUDED (valid export placeholder).
Changes : 2026-04-10 — replaces class schema export (seq 307 → files 010/011).
         2026-04-11 — fix column names per schema.sql:
                      t.tag_name (was t.name / t.tagname).
                      u.symbol only (symbol_ascii not in ontology_core.uom).
*/
SELECT
    COALESCE(plt.code, '')   AS plant_code,
    t.tag_name               AS tag_name,
    p.name                   AS property_name,
    pv.property_value        AS property_value,
    COALESCE(u.symbol, '')   AS property_value_uom
FROM project_core.property_value pv
JOIN project_core.tag           t   ON t.id  = pv.tag_id
JOIN ontology_core.property     p   ON p.id  = pv.property_id
JOIN ontology_core.class_property cp
     ON cp.id = pv.mapping_id
    AND cp.mapping_concept ILIKE '%Functional%'
LEFT JOIN reference_core.plant  plt ON plt.id = t.plant_id
LEFT JOIN ontology_core.uom     u   ON u.code = pv.property_uom_raw
WHERE t.object_status  = 'Active'
  AND pv.object_status = 'Active'
  AND pv.property_value IS NOT NULL
  AND pv.property_value <> ''
ORDER BY t.tag_name, p.name
"""

# ---------------------------------------------------------------------------
# SQL: Physical concept tag instance property values (file 011)
# ---------------------------------------------------------------------------

_EQUIPMENT_PROPERTY_VALUES_SQL = """
/*
Purpose : Equipment (Physical) tag instance property values for EIS file 011.
Gate    : t.object_status = 'Active'
          cp.mapping_concept ILIKE '%Physical%'
          pv.property_value IS NOT NULL AND pv.property_value <> ''
          Rows where value = NULL or '' excluded at SQL level.
          Rows where value = 'TBC' are INCLUDED (valid export placeholder).
Changes : 2026-04-10 — replaces class schema export (seq 307 → files 010/011).
         2026-04-11 — fix column names per schema.sql:
                      t.tag_name (was t.name / t.tagname).
                      u.symbol only (symbol_ascii not in ontology_core.uom).
*/
SELECT
    COALESCE(plt.code, '')   AS plant_code,
    t.tag_name               AS tag_name,
    p.name                   AS property_name,
    pv.property_value        AS property_value,
    COALESCE(u.symbol, '')   AS property_value_uom
FROM project_core.property_value pv
JOIN project_core.tag           t   ON t.id  = pv.tag_id
JOIN ontology_core.property     p   ON p.id  = pv.property_id
JOIN ontology_core.class_property cp
     ON cp.id = pv.mapping_id
    AND cp.mapping_concept ILIKE '%Physical%'
LEFT JOIN reference_core.plant  plt ON plt.id = t.plant_id
LEFT JOIN ontology_core.uom     u   ON u.code = pv.property_uom_raw
WHERE t.object_status  = 'Active'
  AND pv.object_status = 'Active'
  AND pv.property_value IS NOT NULL
  AND pv.property_value <> ''
ORDER BY t.tag_name, p.name
"""

_TAG_PROP_FILE_TEMPLATE   = "JDAW-KVE-E-JA-6944-00001-010-{revision}.CSV"
_EQUIP_PROP_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-011-{revision}.CSV"


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="extract-tag-property-values", retries=1, cache_policy=NO_CACHE)
def extract_tag_property_values(engine: Engine) -> pd.DataFrame:
    """Extract Functional concept tag instance property values (file 010)."""
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_TAG_PROPERTY_VALUES_SQL), conn)
    logger.info(f"Extracted {len(df)} Functional tag property value rows (file 010)")
    return df


@task(name="extract-equipment-property-values", retries=1, cache_policy=NO_CACHE)
def extract_equipment_property_values(engine: Engine) -> pd.DataFrame:
    """Extract Physical concept tag instance property values (file 011)."""
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_EQUIPMENT_PROPERTY_VALUES_SQL), conn)
    logger.info(f"Extracted {len(df)} Physical tag property value rows (file 011)")
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
    Export tag instance property values to EIS CSV snapshots (files 010 + 011).

    Exports tag instance property values for EIS files 010 (Functional)
    and 011 (Physical). Replaces the previous class schema export (seq 307).

    Output files:
      JDAW-KVE-E-JA-6944-00001-010-{doc_revision}.CSV  (Functional tags)
      JDAW-KVE-E-JA-6944-00001-011-{doc_revision}.CSV  (Physical/Equipment tags)

    Column schema (both files, exact EIS order):
      PLANT_CODE, TAG_NAME, PROPERTY_NAME, PROPERTY_VALUE, PROPERTY_VALUE_UOM

    Encoding: UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.

    UoM note:
      PROPERTY_VALUE_UOM = uom.symbol (mixed-case, e.g. "degC", "kPa(g)", "mm2").
      Column is NOT uppercased — EIS and source system are case-sensitive for UoM.

    Args:
        doc_revision: EIS revision code (e.g. "A37"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported_010", "exported_011", "violations".

    Example:
        >>> export_tag_class_properties_flow(doc_revision="A37")
        {'exported_010': 8500, 'exported_011': 3200, 'violations': 12}
    """
    logger = get_run_logger()

    if not re.match(r"^[A-Z]\d{2}$", doc_revision):
        raise ValueError(
            f"doc_revision '{doc_revision}' is invalid. Expected format: [A-Z]\\d{{2}} (e.g. 'A37')."
        )

    engine = create_engine(DB_URL)
    base_dir = Path(output_dir or _EXPORT_DIR)

    # Load UoM alias lookup once for both exports.
    # Maps lower(alias) → symbol for UoM token resolution in _split_value_uom.
    # Returns {} safely if uom_alias table not yet migrated.
    uom_lookup = _load_uom_lookup(engine)
    logger.info(f"Loaded {len(uom_lookup)} UoM alias entries")

    transform_fn = functools.partial(transform_tag_instance_properties, uom_lookup=uom_lookup)

    # --- File 010: Functional tag property values ---
    output_010 = base_dir / _TAG_PROP_FILE_TEMPLATE.format(revision=doc_revision)
    result_010 = run_export_pipeline(
        engine=engine,
        scope="common",
        extract_fn=extract_tag_property_values,
        transform_fn=transform_fn,
        output_path=output_010,
        report_name="tag_property_values_010",
        logger=logger,
    )

    # --- File 011: Physical/Equipment tag property values ---
    output_011 = base_dir / _EQUIP_PROP_FILE_TEMPLATE.format(revision=doc_revision)
    result_011 = run_export_pipeline(
        engine=engine,
        scope="common",
        extract_fn=extract_equipment_property_values,
        transform_fn=transform_fn,
        output_path=output_011,
        report_name="tag_property_values_011",
        logger=logger,
    )

    total_violations = result_010["violations"] + result_011["violations"]
    logger.info(
        f"Export complete: 010={result_010['exported']} rows, "
        f"011={result_011['exported']} rows, violations={total_violations}"
    )

    return {
        "exported_010": result_010["exported"],
        "exported_011": result_011["exported"],
        "violations":   total_violations,
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
