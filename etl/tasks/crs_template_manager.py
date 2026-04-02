"""
Template knowledge base manager for CRS cascade classifier.

Called after each Tier 3 LLM batch to stage new patterns for human review.
LLM results go to audit_core.crs_llm_template_staging — NOT to
audit_core.crs_comment_template (which is a read-only manual reference table).

Human review workflow:
  1. Run sql/queries/review_llm_template_staging.sql to see PendingReview entries.
  2. Approve high-quality entries → INSERT into crs_comment_template manually.
  3. Reject low-quality entries → set object_status='Rejected'.

Only stages results with confidence >= 0.85.
ON CONFLICT (template_hash): increments occurrence_count, never duplicates.
"""
from __future__ import annotations

import hashlib
from typing import Any

from prefect import task, get_run_logger
from prefect.cache_policies import NO_CACHE
from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.tasks.crs_tier1_template_matcher import normalise_comment
from etl.tasks.crs_text_generalizer import generalize_comment


def _hash(normalised: str) -> str:
    """Return MD5 hex digest of lower(trim(text)) — matches Tier 1 lookup."""
    return hashlib.md5(normalised.lower().strip().encode()).hexdigest()


# NO_CACHE: Engine contains weakref objects that cannot be serialized by Prefect
# cache policy. Caching staging writes is also semantically incorrect.
@task(name="update-template-staging", cache_policy=NO_CACHE)
def update_template_db(
    llm_results: list[dict[str, Any]],
    engine: Engine,
    min_confidence: float = 0.85,
    revision: str | None = None,
) -> int:
    """Stage Tier 3 LLM classifications for human review.

    High-confidence LLM results are normalised and written to
    audit_core.crs_llm_template_staging (NOT to crs_comment_template).
    A human must approve staging entries before they become trusted templates.

    ON CONFLICT (template_hash): increments occurrence_count + updates
    last_seen_at and confidence. Does not overwrite human review decisions
    (WHERE object_status = 'PendingReview' guard).

    Args:
        llm_results: Output from run_tier3_llm().
        engine: SQLAlchemy engine.
        min_confidence: Minimum confidence to stage (default 0.85).
        revision: Revision code that triggered this run (e.g. 'A36').

    Returns:
        Number of staging entries inserted or updated.
    """
    logger = get_run_logger()

    # Filter to high-confidence results only; skip generic/unclassified categories
    eligible = [
        r for r in llm_results
        if (r.get("llm_category_confidence") or 0.0) >= min_confidence
        and r.get("llm_category") not in (None, "OTHER", "GENERAL_COMMENT")
    ]

    if not eligible:
        logger.info("Template staging: no eligible results (confidence >= %.2f).", min_confidence)
        return 0

    sql = text("""
        INSERT INTO audit_core.crs_llm_template_staging
            (template_text, template_hash, suggested_category, check_type,
             confidence, llm_response, revision,
             occurrence_count, last_seen_at, created_at, object_status)
        VALUES
            (:template_text, :template_hash, :category, :check_type,
             :confidence, :llm_response, :revision,
             1, now(), now(), 'PendingReview')
        ON CONFLICT (template_hash) DO UPDATE SET
            occurrence_count = audit_core.crs_llm_template_staging.occurrence_count + 1,
            last_seen_at     = now(),
            confidence       = GREATEST(
                                   audit_core.crs_llm_template_staging.confidence,
                                   EXCLUDED.confidence
                               )
        WHERE audit_core.crs_llm_template_staging.object_status = 'PendingReview'
    """)

    # Deduplicate by generalised pattern before building params_list.
    # When N rows share the same error template, only one staging entry is needed
    # per pattern — avoids N redundant upserts that only increment occurrence_count.
    seen_generalized: set[str] = set()
    params_list = []
    for result in eligible:
        raw_text = result.get("comment") or result.get("group_comment") or ""
        if not raw_text:
            continue

        norm = normalise_comment(raw_text)
        if not norm:
            continue

        gen_key = generalize_comment(norm)
        if gen_key in seen_generalized:
            continue
        seen_generalized.add(gen_key)

        params_list.append({
            "template_text": norm,
            "template_hash": _hash(norm),
            "category":      result["llm_category"],
            "check_type":    result.get("check_type"),
            "confidence":    float(result.get("llm_category_confidence", 0.85)),
            "llm_response":  result.get("llm_response"),
            "revision":      revision,
        })

    if not params_list:
        return 0

    with engine.begin() as conn:
        conn.execute(sql, params_list)

    logger.info(
        "Template staging: %d entries added to crs_llm_template_staging (PendingReview). "
        "Run review query to approve/reject. "
        "(from %d eligible Tier 3 results, min_confidence=%.2f)",
        len(params_list), len(eligible), min_confidence,
    )
    return len(params_list)
