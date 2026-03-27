"""
Shared helpers for Phase 2 CRS cascade classifier.

Provides DB engine factory, comment loading, result saving, and tag status lookup.
All DB writes use UPDATE (not INSERT) — crs_comment rows exist from Phase 1 import.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Allow running from repo root: etl/tasks/ → repo root
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from etl.tasks.common import load_config, get_db_engine_url

# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------

_engine: Engine | None = None


def get_engine() -> Engine:
    """Return a module-level SQLAlchemy engine (lazy singleton).

    Uses load_config() + get_db_engine_url() — the existing project pattern.
    Pool sizing: 5 persistent + 10 overflow connections for batch processing.
    """
    global _engine
    if _engine is None:
        config = load_config()
        url = get_db_engine_url(config)
        _engine = create_engine(url, pool_size=5, max_overflow=10)
    return _engine


# ---------------------------------------------------------------------------
# Load comments
# ---------------------------------------------------------------------------

def load_received_comments(limit: int, engine: Engine) -> list[dict[str, Any]]:
    """Fetch crs_comment rows with status='RECEIVED' for classification.

    Args:
        limit: Maximum rows to fetch (use 100 for smoke tests, 5000+ for batches).
        engine: SQLAlchemy engine.

    Returns:
        List of row dicts with all crs_comment columns.
    """
    sql = text("""
        SELECT
            id,
            crs_doc_number,
            comment_id,
            group_comment,
            comment,
            tag_name,
            tag_id,
            property_name,
            document_number,
            detail_sheet,
            from_tag,
            to_tag,
            status,
            row_hash
        FROM audit_core.crs_comment
        WHERE status = 'RECEIVED'
          AND object_status = 'Active'
        ORDER BY crs_doc_number, id
        LIMIT :lim
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"lim": limit}).fetchall()
    return [dict(row._mapping) for row in rows]


# ---------------------------------------------------------------------------
# Prefetch tag statuses
# ---------------------------------------------------------------------------

def prefetch_tag_statuses(
    tag_names: list[str],
    engine: Engine,
) -> dict[str, str]:
    """Batch-fetch tag_status for a list of tag_names.

    Args:
        tag_names: List of tag names to look up.
        engine: SQLAlchemy engine.

    Returns:
        Dict mapping tag_name → tag_status (e.g. 'ACTIVE', 'ASB', 'Inactive').
        Missing tags are absent from the dict (caller treats absence as unknown).
    """
    if not tag_names:
        return {}

    # De-duplicate
    unique_names = list(set(tag_names))

    sql = text("""
        SELECT tag_name, tag_status, object_status
        FROM project_core.tag
        WHERE tag_name = ANY(:names)
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"names": unique_names}).fetchall()

    result: dict[str, str] = {}
    for row in rows:
        # Use object_status='Inactive' as the authoritative soft-delete indicator,
        # but also store tag_status so Tier 0 can check ASB / VOIDED variants.
        result[row.tag_name] = row.tag_status or row.object_status or "Active"
    return result


# ---------------------------------------------------------------------------
# Save classification results (UPDATE, never INSERT)
# ---------------------------------------------------------------------------

def save_classification_results(
    results: list[dict[str, Any]],
    engine: Engine,
    run_id: str,  # noqa: ARG001  (reserved for future audit_core.sync_run_stats)
) -> int:
    """Batch-UPDATE crs_comment rows with classification output.

    crs_comment rows are created in Phase 1 (import). This function only
    updates the classification columns — it never inserts new rows.

    Args:
        results: List of dicts, each must contain 'id' (UUID str) plus
                 classification fields (may be partial — missing keys = NULL).
        engine: SQLAlchemy engine.
        run_id: Prefect run ID (reserved for future audit logging).

    Returns:
        Number of rows updated.
    """
    if not results:
        return 0

    sql = text("""
        UPDATE audit_core.crs_comment SET
            llm_category             = :llm_category,
            llm_category_confidence  = :confidence,
            llm_response             = :llm_response,
            llm_model_used           = :llm_model,
            status                   = :status,
            classification_tier      = :tier,
            template_id              = :template_id,
            sync_timestamp           = now()
        WHERE id = :id
    """)

    params = [
        {
            "id":           str(r["id"]),
            "llm_category": r.get("llm_category"),
            "confidence":   r.get("llm_category_confidence"),
            "llm_response": r.get("llm_response"),
            "llm_model":    r.get("llm_model_used"),
            "status":       r.get("status", "CLASSIFIED"),
            "tier":         r.get("classification_tier"),
            "template_id":  r.get("template_id"),
        }
        for r in results
    ]

    with engine.begin() as conn:
        conn.execute(sql, params)

    return len(params)
