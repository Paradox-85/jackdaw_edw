"""
Phase 2 CRS Cascade Classifier — main orchestration flow.

4-tier cascade reduces LLM usage by 95%:
  Tier 0  (~5-10%) : Deterministic skip (informational, unknown tags, inactive tags)
  Tier 1  (50-70%) : Knowledge base template matching (exact + fuzzy, threshold 0.92)
  Tier 2  (15-20%) : Keyword rules + detail_sheet name classification
  Tier 3   (5-10%) : Qwen3 LLM (only for unclear/complex comments)

After each Tier 3 batch, results are fed back into the KB (template_manager).
Subsequent batches will have higher Tier 1 coverage and lower LLM load.

Usage:
    # Smoke test — 100 comments
    python etl/flows/classify_crs_comments.py --limit 100

    # Debug run scoped to a single revision
    python etl/flows/classify_crs_comments.py --revision A36

    # Debug run: first 50 comments of revision A36
    python etl/flows/classify_crs_comments.py --revision A36 --limit 50 --batch-size 50

    # Integration test — 5000 comments
    python etl/flows/classify_crs_comments.py --limit 5000

    # Full production run (default)
    python etl/flows/classify_crs_comments.py
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

from prefect import flow, get_run_logger

# Allow running from repo root
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from etl.tasks.crs_helpers import (
    get_engine,
    load_received_comments,
    save_classification_results,
)
from etl.tasks.crs_tier0_prefilter import run_tier0
from etl.tasks.crs_tier1_template_matcher import run_tier1
from etl.tasks.crs_tier2_keyword_classifier import run_tier2
from etl.tasks.crs_tier3_llm_classifier import run_tier3_llm
from etl.tasks.crs_template_manager import update_template_db


@flow(name="classify-crs-comments-cascade", log_prints=True)
def classify_crs_comments_cascade(
    limit: int = 0,
    batch_size: int = 500,
    revision_filter: str | None = None,
) -> dict[str, int]:
    """4-tier cascade classifier for CRS comments.

    Args:
        limit: Max comments to process. 0 = all RECEIVED comments.
        batch_size: Comments per processing batch (default 500).
        revision_filter: Optional revision code to restrict scope (e.g. 'A36').
                         When provided, only comments from that revision are loaded.
                         When None (default), all RECEIVED comments are loaded.

    Returns:
        Stats dict: {tier0, tier1, tier2, tier3, saved, total}.
    """
    logger = get_run_logger()
    engine = get_engine()
    run_id = str(uuid.uuid4())

    fetch_limit = limit if limit > 0 else 9_999_999
    logger.info(
        "CRS Cascade Classifier starting — run_id=%s, revision=%s, limit=%s, batch_size=%d",
        run_id,
        revision_filter or "ALL",
        limit if limit > 0 else "ALL",
        batch_size,
    )

    comments = load_received_comments(
        limit=fetch_limit,
        engine=engine,
        revision_filter=revision_filter,
    )
    total = len(comments)

    if total == 0:
        logger.info(
            "No RECEIVED comments found (revision=%s) — nothing to classify.",
            revision_filter or "ALL",
        )
        return {"tier0": 0, "tier1": 0, "tier2": 0, "tier3": 0, "saved": 0, "total": 0}

    logger.info(
        "Loaded %d RECEIVED comments for classification (revision=%s).",
        total,
        revision_filter or "ALL",
    )

    stats: dict[str, int] = {"tier0": 0, "tier1": 0, "tier2": 0, "tier3": 0, "saved": 0, "total": total}
    all_results: list = []

    for batch_start in range(0, total, batch_size):
        batch = comments[batch_start : batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        logger.info("Batch %d/%d — %d comments", batch_num, total_batches, len(batch))

        # --- Tier 0: Pre-filter ---
        batch, t0_results = run_tier0(batch, engine)
        stats["tier0"] += len(t0_results)
        all_results.extend(t0_results)

        if not batch:
            continue

        # --- Tier 1: Template knowledge base ---
        batch, t1_results = run_tier1(batch, engine)
        stats["tier1"] += len(t1_results)
        all_results.extend(t1_results)

        if not batch:
            continue

        # --- Tier 2: Keyword rules + sheet name classification ---
        batch, t2_results = run_tier2(batch)
        stats["tier2"] += len(t2_results)
        all_results.extend(t2_results)

        if not batch:
            continue

        # --- Tier 3: LLM (only remaining ~5-10%) ---
        t3_results = run_tier3_llm(batch, engine)
        stats["tier3"] += len(t3_results)
        all_results.extend(t3_results)

        # Auto-populate KB from Tier 3 — makes next batches faster
        update_template_db(t3_results, engine)

    # Normalisation: ensure category_code is set when llm_category starts with CRS-C
    for r in all_results:
        if not r.get("category_code") and r.get("llm_category", "").startswith("CRS-C"):
            r["category_code"] = r["llm_category"]
            r["category_confidence"] = r.get("llm_category_confidence")

    # Save all results to DB (batch UPDATE)
    saved = save_classification_results(all_results, engine, run_id)
    stats["saved"] = saved

    # Summary log
    classified_total = stats["tier0"] + stats["tier1"] + stats["tier2"] + stats["tier3"]
    pct = lambda n: f"{100 * n / classified_total:.1f}%" if classified_total else "0%"  # noqa: E731

    logger.info("=" * 60)
    logger.info("CRS CASCADE CLASSIFICATION COMPLETE")
    logger.info("  Revision scope:       %s", revision_filter or "ALL")
    logger.info("  Total comments:       %d", total)
    logger.info("  Tier 0 (skipped):     %d (%s)", stats["tier0"], pct(stats["tier0"]))
    logger.info("  Tier 1 (KB match):    %d (%s)", stats["tier1"], pct(stats["tier1"]))
    logger.info("  Tier 2 (keyword):     %d (%s)", stats["tier2"], pct(stats["tier2"]))
    logger.info("  Tier 3 (LLM):         %d (%s)", stats["tier3"], pct(stats["tier3"]))
    logger.info("  DB rows updated:      %d", saved)
    logger.info("=" * 60)

    return stats


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="CRS Phase 2 — 4-tier cascade comment classifier"
    )
    parser.add_argument(
        "--run", action="store_true",
        help="Run classifier directly (local execution). Default behaviour (no flags) registers deployment.",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Max comments to process (0 = all RECEIVED). Used with --run.",
    )
    parser.add_argument(
        "--batch-size", type=int, default=500,
        help="Comments per processing batch (default 500). Used with --run.",
    )
    parser.add_argument(
        "--revision", type=str, default=None,
        help="Restrict to a single revision code, e.g. A36. Used with --run.",
    )

    args = parser.parse_args()

    if args.run:
        result = classify_crs_comments_cascade(
            limit=args.limit,
            batch_size=args.batch_size,
            revision_filter=args.revision,
        )
        print(result)
    else:
        # Default: register Prefect deployment.
        # Called without args by deploy_all.py — must deploy, not run.
        classify_crs_comments_cascade.from_source(
            source=str(_REPO_ROOT),
            entrypoint="etl/flows/classify_crs_comments_deploy.py:classify_crs_comments_cascade",
        ).deploy(
            name="classify_crs_comments_cascade",
            work_pool_name="default-agent-pool",
            parameters={"limit": 0, "batch_size": 500, "revision_filter": None},
        )
