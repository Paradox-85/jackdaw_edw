"""Reverse ETL export flow: Tag Physical Connections (EIS seq 212)."""

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
    from tasks.export_transforms import transform_tag_connections
    from tasks.export_pipeline import run_export_pipeline
except ImportError as e:
    print(f"[SKIP] {Path(__file__).name}: Could not import task modules. Details: {e}")
    sys.exit(0)

# Module-level config — same pattern as other export flows
config = load_config()
DB_URL = get_db_engine_url(config)
_EXPORT_DIR = config.get("storage", {}).get("export_dir", ".")

# ---------------------------------------------------------------------------
# SQL: Extract physical connections for active non-VOID/Future tags
# ---------------------------------------------------------------------------

_TAG_CONNECTIONS_SQL = """
/*
Purpose: Tag physical connections export for EIS snapshot (seq 212).
Gate:    t.object_status = 'Active' AND tag_status not VOID/Future/empty
         AND at least one connection field (from_tag_raw / to_tag_raw) is non-empty.
Note:    from_tag_raw / to_tag_raw exported verbatim — no FK resolution.
         Values may contain open-end labels, zone comments, or free text from source.
Changes: 2026-03-16 — Initial implementation.
         2026-04-09 — Add DISTINCT + self-loop exclusion guard.
         2026-04-09 - ORDER BY removed: incompatible with SELECT DISTINCT (t.tag_name not in select list)
*/
SELECT DISTINCT
    p.code          AS plant_code,
    t.from_tag_raw  AS from_tag_name,
    t.to_tag_raw    AS to_tag_name
FROM project_core.tag t
-- Why LEFT JOIN: tag must not disappear if plant FK is missing
LEFT JOIN reference_core.plant p ON t.plant_id = p.id
WHERE t.object_status = 'Active'
  AND t.tag_status NOT IN ('VOID', 'Future')
  AND t.tag_status IS NOT NULL
  AND t.tag_status != ''
  AND (
       (t.from_tag_raw IS NOT NULL AND t.from_tag_raw != '')
    OR (t.to_tag_raw  IS NOT NULL AND t.to_tag_raw  != '')
  )
  AND (t.from_tag_raw IS NULL OR t.to_tag_raw IS NULL
       OR t.from_tag_raw != t.to_tag_raw)  -- exclude self-loop at SQL level
"""

_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-006-{revision}.CSV"


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="extract-tag-connections", retries=1, cache_policy=NO_CACHE)
def extract_tag_connections(engine: Engine) -> pd.DataFrame:
    """
    Run the Tag Physical Connections SQL query and return a raw DataFrame.

    Args:
        engine: SQLAlchemy engine connected to engineering_core.

    Returns:
        DataFrame with active tag connection rows (from_tag_raw / to_tag_raw).
    """
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_TAG_CONNECTIONS_SQL), conn)
    logger.info(f"Extracted {len(df)} tag connection rows")
    return df


# ---------------------------------------------------------------------------
# Prefect flow
# ---------------------------------------------------------------------------

@flow(name="export_tag_connections_data", log_prints=True)
def export_tag_connections_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Tag Physical Connections to EIS CSV snapshot (seq 212).

    Output file: JDAW-KVE-E-JA-6944-00001-006-{doc_revision}.CSV
    Encoding:    UTF-8 BOM (utf-8-sig) for Excel/EIS compatibility.
    Filter gate: object_status = 'Active', tag_status NOT IN ('VOID', 'Future').
    Audit:       Start/end recorded in audit_core.sync_run_stats.

    Args:
        doc_revision: EIS revision code (e.g. "A35"). Must match [A-Z]\\d{2}.
        output_dir: Destination directory. Defaults to config storage.export_dir.

    Returns:
        dict with keys "exported" (rows written) and "violations" (total violations found).

    Raises:
        ValueError: If doc_revision does not match [A-Z]\\d{2} pattern.

    Example:
        >>> export_tag_connections_flow(doc_revision="A35")
        {'exported': 4591, 'violations': 0}
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
        scope="tag_connection",
        extract_fn=extract_tag_connections,
        transform_fn=transform_tag_connections,
        output_path=output_path,
        report_name="tag_connections",
        logger=logger,
    )


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    export_tag_connections_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/export_tag_connections_deploy.py:export_tag_connections_flow",
    ).deploy(
        name="export_tag_connections_data_deploy",
        work_pool_name="default-agent-pool",
    )
