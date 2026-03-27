"""
Template knowledge base manager for CRS cascade classifier.

Called after each Tier 3 LLM batch to auto-populate crs_comment_template.
This is the key mechanism that makes subsequent batches progressively faster:
  - After batch 1: ~0% Tier 1 coverage (empty KB)
  - After batch 2: ~30-40% Tier 1 coverage (common patterns cached)
  - After batch 3-4: ~50-70% Tier 1 coverage (steady state)

Only inserts templates with confidence >= 0.85 (high-quality LLM outputs only).
ON CONFLICT (template_hash) increments usage_count — never duplicates.
"""
from __future__ import annotations

import hashlib
from typing import Any

from prefect import task, get_run_logger
from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.tasks.crs_tier1_template_matcher import normalise_comment


def _hash(normalised: str) -> str:
    """Return MD5 hex digest of lower(trim(text)) — matches Tier 1 lookup."""
    return hashlib.md5(normalised.lower().strip().encode()).hexdigest()


@task(name="update-template-db")
def update_template_db(
    llm_results: list[dict[str, Any]],
    engine: Engine,
    min_confidence: float = 0.85,
) -> int:
    """Upsert Tier 3 LLM classifications into the template knowledge base.

    High-confidence LLM results are normalised and stored so Tier 1 can
    match them in future batches — no LLM call needed for repeat patterns.

    Args:
        llm_results: Output from run_tier3_llm().
        engine: SQLAlchemy engine.
        min_confidence: Minimum confidence to store (default 0.85).

    Returns:
        Number of templates upserted (new + updated).
    """
    logger = get_run_logger()

    # Filter to high-confidence results only
    eligible = [
        r for r in llm_results
        if (r.get("llm_category_confidence") or 0.0) >= min_confidence
        and r.get("llm_category") not in (None, "OTHER", "GENERAL_COMMENT")
    ]

    if not eligible:
        logger.info("Template DB: no eligible results (confidence >= %.2f).", min_confidence)
        return 0

    sql = text("""
        INSERT INTO audit_core.crs_comment_template
            (template_text, template_hash, category, check_type,
             confidence, source, usage_count, last_used_at, created_at, object_status)
        VALUES
            (:template_text, :template_hash, :category, :check_type,
             :confidence, 'llm', 1, now(), now(), 'Active')
        ON CONFLICT (template_hash) DO UPDATE SET
            usage_count  = audit_core.crs_comment_template.usage_count + 1,
            last_used_at = now(),
            -- Update confidence if new result is more confident
            confidence   = GREATEST(
                               audit_core.crs_comment_template.confidence,
                               EXCLUDED.confidence
                           )
    """)

    params_list = []
    for result in eligible:
        raw_text = result.get("comment") or result.get("group_comment") or ""
        if not raw_text:
            continue

        norm = normalise_comment(raw_text)
        if not norm:
            continue

        params_list.append({
            "template_text": norm,
            "template_hash": _hash(norm),
            "category":      result["llm_category"],
            "check_type":    result.get("check_type"),
            "confidence":    float(result.get("llm_category_confidence", 0.85)),
        })

    if not params_list:
        return 0

    with engine.begin() as conn:
        conn.execute(sql, params_list)

    logger.info(
        "Template DB: %d entries upserted (from %d eligible Tier 3 results, "
        "min_confidence=%.2f).",
        len(params_list), len(eligible), min_confidence,
    )
    return len(params_list)
