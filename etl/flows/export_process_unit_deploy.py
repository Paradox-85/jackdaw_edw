"""Reverse ETL export flow: Process Unit Register (EIS seq 204)."""

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
    from tasks.export_transforms import transform_process_unit
    from tasks.export_pipeline import run_export_pipeline
except ImportError as e:
    print(f"[SKIP] {Path(__file__).name}: Could not import task modules. Details: {e}")
    sys.exit(0)

# Module-level config — same pattern as other export flows
config = load_config()
DB_URL = get_db_engine_url(config)
_EXPORT_DIR = config.get("storage", {}).get("export_dir", ".")

# ---------------------------------------------------------------------------
# SQL: Extract active process units with active tag count
# ---------------------------------------------------------------------------

_PROCESS_UNIT_SQL = """
/*
Purpose: Process Unit Register full extract for EIS snapshot export (seq 204).
Gate:    u.object_status = 'Active'
Note:    COUNT_OF_TAGS counts only Active tags — informational field per EIS spec.
         plant_code_raw is denormalised in each process_unit row.
Changes: 2026-03-13 — Initial implementation.
*/
SELECT
    u.plant_code_raw                    AS PLANT_CODE,
    u.code                              AS PROCESS_UNIT_CODE,
    u.name                              AS PROCESS_UNIT_NAME,
    COUNT(t.id)                         AS COUNT_OF_TAGS
FROM reference_core.process_unit u
-- Why LEFT JOIN: units with zero tags must still appear in the register
LEFT JOIN project_core.tag t
    ON t.process_unit_id = u.id AND t.object_status = 'Active'
WHERE u.object_status = 'Active'
GROUP BY u.plant_code_raw, u.id, u.code, u.name
ORDER BY u.plant_code_raw, u.code
"""

_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-002-{revision}.CSV"


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="extract-process-unit", retries=1, cache_policy=NO_CACHE)
def extract_process_unit(engine: Engine) -> pd.DataFrame:
    """
    Run the Process Unit Register SQL query and return a raw DataFrame.

    Args:
        engine: SQLAlchemy engine connected to engineering_core.

    Returns:
        DataFrame with all active process units and their tag counts.
    """
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_PROCESS_UNIT_SQL), conn)
    logger.info(f"Extracted {len(df)} active process unit rows")
    return df


# ---------------------------------------------------------------------------
# Prefect flow
# ---------------------------------------------------------------------------

@flow(name="export_process_unit_data", log_prints=True)
def export_process_unit_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Process Unit Register to EIS CSV snapshot (seq 204).

    Output file: JDAW-KVE-E-JA-6944-00001-002-{doc_revision}.CSV
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
        >>> export_process_unit_flow(doc_revision="A35")
        {'exported': 37, 'violations': 0}
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
        scope="process_unit",
        extract_fn=extract_process_unit,
        transform_fn=transform_process_unit,
        output_path=output_path,
        report_name="process_unit",
        logger=logger,
    )


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    export_process_unit_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/export_process_unit_deploy.py:export_process_unit_flow",
    ).deploy(
        name="export_process_unit_data_deploy",
        work_pool_name="default-agent-pool",
    )
