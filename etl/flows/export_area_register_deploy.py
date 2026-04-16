"""Reverse ETL export flow: Area Register (EIS seq 203)."""

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
    from tasks.export_transforms import transform_area_register
    from tasks.export_pipeline import run_export_pipeline
except ImportError as e:
    print(f"[SKIP] {Path(__file__).name}: Could not import task modules. Details: {e}")
    sys.exit(0)

# Module-level config — same pattern as other export flows
config = load_config()
DB_URL = get_db_engine_url(config)
_EXPORT_DIR = config.get("storage", {}).get("export_dir", ".")

# ---------------------------------------------------------------------------
# SQL: Extract active areas with resolved plant name
# ---------------------------------------------------------------------------

_AREA_REGISTER_SQL = """
/*
Purpose: Area Register full extract for EIS snapshot export (seq 203).
Gate:    a.object_status = 'Active'
Note:    plant_code_raw is denormalised into each area row — JOIN to plant
         is needed only to resolve the plant display name (PLANT_REF).
Changes: 2026-03-13 — Initial implementation.
*/
SELECT
    a.plant_code_raw                    AS PLANT_CODE,
    a.code                              AS AREA_CODE,
    a.name                              AS AREA_NAME,
    COALESCE(a.main_area_code, '')      AS MAIN_AREA_CODE,
    COALESCE(pl.name, '')               AS PLANT_REF
FROM reference_core.area a
-- Why LEFT JOIN: area must not disappear if plant FK is missing (data integrity guard)
LEFT JOIN reference_core.plant pl ON pl.code = a.plant_code_raw
WHERE a.object_status = 'Active'
ORDER BY a.plant_code_raw, a.code
"""

_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-001-{revision}.CSV"


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="extract-area-register", retries=1, cache_policy=NO_CACHE)
def extract_area_register(engine: Engine) -> pd.DataFrame:
    """
    Run the Area Register SQL query and return a raw DataFrame.

    Args:
        engine: SQLAlchemy engine connected to engineering_core.

    Returns:
        DataFrame with all active area rows and resolved plant name.
    """
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_AREA_REGISTER_SQL), conn)
    logger.info(f"Extracted {len(df)} active area rows")
    return df


# ---------------------------------------------------------------------------
# Prefect flow
# ---------------------------------------------------------------------------

@flow(name="export_area_register_data", log_prints=True)
def export_area_register_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Area Register to EIS CSV snapshot (seq 203).

    Output file: JDAW-KVE-E-JA-6944-00001-001-{doc_revision}.CSV
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
        >>> export_area_register_flow(doc_revision="A35")
        {'exported': 205, 'violations': 0}
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
        scope="area",
        extract_fn=extract_area_register,
        transform_fn=transform_area_register,
        output_path=output_path,
        report_name="area_register",
        logger=logger,
    )


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    export_area_register_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/export_area_register_deploy.py:export_area_register_flow",
    ).deploy(
        name="export_area_register_data_deploy",
        work_pool_name="default-agent-pool",
    )
