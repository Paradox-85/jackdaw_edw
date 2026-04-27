"""
Phase 3 CRS Validate & Respond — main orchestration flow.

Runs batch validation queries against IN_REVIEW comments, then generates
formal_response from validation results.

Prerequisites:
  - Phase 2 classify flow must have run (comments status = 'IN_REVIEW').
  - migration_027_crs_phase3_seed.sql must be applied (populates crs_validation_query).
  - migration_028_crs_phase3_map.sql must be applied (populates crs_template_query_map).

Usage:
    # Smoke test — one category
    python etl/flows/validate_crs_comments_deploy.py --run --category CRS-C001

    # Dry run — validate queries but do NOT write to DB
    python etl/flows/validate_crs_comments_deploy.py --run --dry-run

    # Validation only (skip response generation)
    python etl/flows/validate_crs_comments_deploy.py --run --skip-evaluation

    # Full production run
    python etl/flows/validate_crs_comments_deploy.py --run
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path

from prefect import flow, get_run_logger
from sqlalchemy import text

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from etl.tasks.crs_helpers import get_engine
from etl.tasks.crs_batch_validator import run_batch_validation
from etl.tasks.crs_cascade_evaluator import evaluate_validation_results


# ---------------------------------------------------------------------------
# Audit helpers
# ---------------------------------------------------------------------------

def _log_run_start(engine, run_id: str) -> None:
    sql = text("""
        INSERT INTO audit_core.sync_run_stats
            (run_id, target_table, start_time, source_file)
        VALUES (:rid, :tbl, :st, :sf)
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "rid": run_id,
            "tbl": "audit_core.crs_comment_validation",
            "st":  datetime.now(),
            "sf":  "validate_crs_comments_deploy.py",
        })


def _log_run_end(engine, run_id: str, stats: dict) -> None:
    sql = text("""
        UPDATE audit_core.sync_run_stats SET
            end_time        = :et,
            count_created   = :cr,
            count_updated   = :up,
            count_unchanged = :uc,
            count_errors    = :er
        WHERE run_id = :rid
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "et":  datetime.now(),
            "cr":  stats.get("results_written", 0),
            "up":  stats.get("responded", 0) + stats.get("rationale_set", 0),
            "uc":  stats.get("deferred", 0),
            "er":  stats.get("errors", 0),
            "rid": run_id,
        })


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------

@flow(name="validate-crs-comments", log_prints=True)
def validate_crs_comments(
    batch_size: int = 500,
    category_filter: str | None = None,
    dry_run: bool = False,
    skip_evaluation: bool = False,
) -> dict[str, int]:
    """Phase 3: validate IN_REVIEW CRS comments and generate formal responses.

    Args:
        batch_size: DB write batch size for validation results (default 500).
        category_filter: Restrict validation to one category code (e.g. 'CRS-C001').
        dry_run: Execute validation queries but write nothing to DB.
        skip_evaluation: Run batch validation only, skip cascade evaluator.

    Returns:
        Combined stats from batch_validator and cascade_evaluator.
    """
    logger = get_run_logger()
    engine = get_engine()
    run_id = str(uuid.uuid4())

    logger.info(
        "CRS Phase 3 Validate starting — run_id=%s category=%s batch_size=%d "
        "dry_run=%s skip_evaluation=%s",
        run_id,
        category_filter or "ALL",
        batch_size,
        dry_run,
        skip_evaluation,
    )

    if not dry_run:
        _log_run_start(engine, run_id)

    # Step 1: Batch validation
    batch_stats = run_batch_validation(
        engine=engine,
        batch_size=batch_size,
        category_filter=category_filter,
        dry_run=dry_run,
    )

    # Step 2: Cascade evaluation
    eval_stats: dict[str, int] = {
        "evaluated": 0, "responded": 0, "rationale_set": 0,
        "deferred": 0, "errors": 0,
    }
    if not skip_evaluation:
        eval_stats = evaluate_validation_results(engine=engine, dry_run=dry_run)

    combined = {**batch_stats, **eval_stats, "run_id_str": run_id}

    if not dry_run:
        _log_run_end(engine, run_id, combined)

    logger.info("=" * 60)
    if dry_run:
        logger.info("DRY-RUN complete — no DB writes performed.")
    else:
        logger.info("CRS PHASE 3 VALIDATION COMPLETE")
    logger.info("  Category scope:     %s", category_filter or "ALL")
    logger.info("  Categories checked: %d", batch_stats.get("categories_checked", 0))
    logger.info("  Queries run:        %d", batch_stats.get("queries_run", 0))
    logger.info("  Comments validated: %d", batch_stats.get("comments_validated", 0))
    logger.info("  Results written:    %d", batch_stats.get("results_written", 0))
    if not skip_evaluation:
        logger.info("  Responses generated:%d", eval_stats.get("responded", 0))
        logger.info("  Rationale set:      %d", eval_stats.get("rationale_set", 0))
        logger.info("  Deferred (no write):%d", eval_stats.get("deferred", 0))
    logger.info("  Errors:             %d",
                batch_stats.get("errors", 0) + eval_stats.get("errors", 0))
    logger.info("=" * 60)

    return combined


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="CRS Phase 3 — batch validation and formal response generation"
    )
    parser.add_argument(
        "--run", action="store_true",
        help="Run flow directly (local execution). Without flag: register Prefect deployment.",
    )
    parser.add_argument(
        "--batch-size", type=int, default=500,
        dest="batch_size",
        help="DB write batch size for validation results (default 500).",
    )
    parser.add_argument(
        "--category", type=str, default=None,
        help="Restrict to one category code, e.g. CRS-C001.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="Execute validation queries but write nothing to DB.",
    )
    parser.add_argument(
        "--skip-evaluation", action="store_true", dest="skip_evaluation",
        help="Run batch validation only; skip cascade evaluator.",
    )

    args = parser.parse_args()

    if args.run:
        result = validate_crs_comments(
            batch_size=args.batch_size,
            category_filter=args.category,
            dry_run=args.dry_run,
            skip_evaluation=args.skip_evaluation,
        )
        print(result)
    else:
        validate_crs_comments.from_source(
            source=str(_REPO_ROOT),
            entrypoint="etl/flows/validate_crs_comments_deploy.py:validate_crs_comments",
        ).deploy(
            name="validate_crs_comments",
            work_pool_name="default-agent-pool",
            parameters={"batch_size": 500, "category_filter": None},
        )
