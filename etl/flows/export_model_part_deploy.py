"""Reverse ETL export flow: Model Part Register (EIS seq 209)."""

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
    from tasks.export_transforms import transform_model_part
    from tasks.export_pipeline import run_export_pipeline
except ImportError as e:
    print(f"[SKIP] {Path(__file__).name}: Could not import task modules. Details: {e}")
    sys.exit(0)

# Module-level config — same pattern as other export flows
config = load_config()
DB_URL = get_db_engine_url(config)
_EXPORT_DIR = config.get("storage", {}).get("export_dir", ".")

# ---------------------------------------------------------------------------
# SQL: Extract active model parts
# ---------------------------------------------------------------------------

_MODEL_PART_SQL = """
/*
Purpose: Model Part Register extract for EIS snapshot export (seq 209).
Gate:    t.object_status = 'Active', tag_status NOT IN ('VOID', ''), t.model_id NOT NULL.
Note:    Source is project_core.tag joined to model_part via tag.model_id (direct FK).
         MANUFACTURER_COMPANY_NAME and EQUIPMENT_CLASS_NAME are LEFT JOIN — empty if FK unresolved.
Changes: 2026-03-13 — Initial implementation.
         2026-03-17 — Reworked: source changed to project_core.tag via tag.model_id FK;
                      added MANUFACTURER_COMPANY_NAME, EQUIPMENT_CLASS_NAME, MODEL_DESCRIPTION.
*/
SELECT
    COALESCE(pl.code, 'JDA')            AS PLANT_CODE,
    mp.code                             AS MODEL_PART_CODE,
    COALESCE(c_mfr.name, '')            AS MANUFACTURER_COMPANY_NAME,
    COALESCE(mp.name, '')               AS MODEL_PART_NAME,
    COALESCE(cls.name, '')              AS EQUIPMENT_CLASS_NAME,
    COALESCE(mp.definition, '')         AS MODEL_DESCRIPTION,
    mp.object_status
FROM project_core.tag t
INNER JOIN reference_core.model_part mp  ON t.model_id         = mp.id
LEFT  JOIN reference_core.company c_mfr  ON mp.manufacturer_id = c_mfr.id
LEFT  JOIN ontology_core.class cls       ON t.class_id         = cls.id
LEFT  JOIN reference_core.plant pl       ON t.plant_id         = pl.id
WHERE t.object_status = 'Active'
  AND UPPER(COALESCE(t.tag_status, '')) NOT IN ('VOID', '')
  AND t.model_id IS NOT NULL
ORDER BY mp.code, t.tag_name
"""

_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-005-{revision}.CSV"


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="extract-model-part", retries=1, cache_policy=NO_CACHE)
def extract_model_part(engine: Engine) -> pd.DataFrame:
    """
    Run the Model Part Register SQL query and return a raw DataFrame.

    Args:
        engine: SQLAlchemy engine connected to engineering_core.

    Returns:
        DataFrame with all active model part rows.
    """
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_MODEL_PART_SQL), conn)
    logger.info(f"Extracted {len(df)} active model part rows")
    return df


# ---------------------------------------------------------------------------
# Prefect flow
# ---------------------------------------------------------------------------

@flow(name="export_model_part_data", log_prints=True)
def export_model_part_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Model Part Register to EIS CSV snapshot (seq 209).

    Output file: JDAW-KVE-E-JA-6944-00001-005-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: object_status = 'Active' (SQL layer).
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A35"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations" (total violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.

    Example:
        >>> export_model_part_flow(doc_revision="A35")
        {'exported': 1275, 'violations': 0}
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
        scope="model_part",
        extract_fn=extract_model_part,
        transform_fn=transform_model_part,
        output_path=output_path,
        report_name="model_part",
        logger=logger,
    )


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    export_model_part_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/export_model_part_deploy.py:export_model_part_flow",
    ).deploy(
        name="export_model_part_data_deploy",
        work_pool_name="default-agent-pool",
    )
