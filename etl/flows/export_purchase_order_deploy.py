"""Reverse ETL export flow: Purchase Order Register (EIS seq 214)."""

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
    from tasks.export_transforms import transform_purchase_order
    from tasks.export_pipeline import run_export_pipeline
except ImportError as e:
    print(f"[SKIP] {Path(__file__).name}: Could not import task modules. Details: {e}")
    sys.exit(0)

# Module-level config — same pattern as other export flows
config = load_config()
DB_URL = get_db_engine_url(config)
_EXPORT_DIR = config.get("storage", {}).get("export_dir", ".")

# ---------------------------------------------------------------------------
# SQL: Extract active purchase orders
# ---------------------------------------------------------------------------

_PURCHASE_ORDER_SQL = """
/*
Purpose: Purchase Order Register full extract for EIS snapshot export (seq 214).
Gate:    po.object_status = 'Active'
Note:    purchase_order has no plant_id FK — PLANT_CODE hardcoded to 'JDA' (Jackdaw plant).
         po_date stored as TEXT in source format (DD.MM.YYYY) — passed as-is.
         issuer/receiver company raw included for validation rules, dropped by transform.
Changes: 2026-03-13 — Initial implementation.
*/
SELECT
    'JDA'                               AS PLANT_CODE,
    po.code                             AS PO_CODE,
    COALESCE(po.name, '')               AS PO_TITLE,
    COALESCE(po.po_date, '')            AS PO_DATE,
    po.object_status                    AS PO_STATUS,
    -- raw FK fields for validation rules (dropped by transform before CSV write)
    po.issuer_company_raw,
    po.receiver_company_raw
FROM reference_core.purchase_order po
WHERE po.object_status = 'Active'
ORDER BY po.code
"""

_FILE_TEMPLATE = "JDAW-KVE-E-JA-6944-00001-008-{revision}.CSV"


# ---------------------------------------------------------------------------
# Prefect tasks
# ---------------------------------------------------------------------------

@task(name="extract-purchase-order", retries=1, cache_policy=NO_CACHE)
def extract_purchase_order(engine: Engine) -> pd.DataFrame:
    """
    Run the Purchase Order Register SQL query and return a raw DataFrame.

    Args:
        engine: SQLAlchemy engine connected to engineering_core.

    Returns:
        DataFrame with all active purchase order rows.
    """
    logger = get_run_logger()
    with engine.connect() as conn:
        df = pd.read_sql(text(_PURCHASE_ORDER_SQL), conn)
    logger.info(f"Extracted {len(df)} active purchase order rows")
    return df


# ---------------------------------------------------------------------------
# Prefect flow
# ---------------------------------------------------------------------------

@flow(name="export-purchase-order", log_prints=True)
def export_purchase_order_flow(
    doc_revision: str = "A35",
    output_dir: str | None = None,
) -> dict[str, int]:
    """
    Export Purchase Order Register to EIS CSV snapshot (seq 214).

    Output file: JDAW-KVE-E-JA-6944-00001-008-{doc_revision}.CSV
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
        >>> export_purchase_order_flow(doc_revision="A35")
        {'exported': 1730, 'violations': 0}
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
        scope="purchase_order",
        extract_fn=extract_purchase_order,
        transform_fn=transform_purchase_order,
        output_path=output_path,
        report_name="purchase_order",
        logger=logger,
    )


if __name__ == "__main__":
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    export_purchase_order_flow.from_source(
        source=str(_REPO_ROOT),
        entrypoint="etl/flows/export_purchase_order_deploy.py:export_purchase_order_flow",
    ).deploy(
        name="export-purchase-order-deployment",
        work_pool_name="default-agent-pool",
    )
