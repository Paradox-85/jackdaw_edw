"""
Phase 3 CRS Batch Validator.

Runs GROUP validation queries for all IN_REVIEW comments, grouped by category_code.
One SQL call per (category, query) pair via ANY(:tag_names) — no N+1 queries.

Algorithm:
  1. Load all GROUP queries from audit_core.v_template_queries.
  2. For each (category_code, query_id) pair:
     a. Collect tag_names of all IN_REVIEW comments with that category.
     b. Execute GROUP query with :tag_names = all tag names.
     c. Map rows back to individual comments via group_by_field (default: tag_name).
     d. Apply evaluation_strategy → PASSED / FAILED / DEFERRED / INCONCLUSIVE.
     e. UPSERT rows into audit_core.crs_comment_validation.
     f. Append query_id to audit_core.crs_comment.validation_query_ids.
  3. Return stats dict.

Speed: One DB round-trip per (category, query) pair regardless of comment count.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from prefect import get_run_logger, task
from prefect.cache_policies import NO_CACHE
from sqlalchemy import text
from sqlalchemy.engine import Engine


# ---------------------------------------------------------------------------
# Query loader
# ---------------------------------------------------------------------------

def _load_group_queries(engine: Engine) -> list[dict[str, Any]]:
    """Return all active GROUP queries from v_template_queries."""
    sql = text("""
        SELECT DISTINCT
            template_category,
            query_id,
            query_code,
            query_type,
            evaluation_strategy,
            has_parameters,
            parameter_names,
            sql_query,
            response_template,
            group_by_field,
            expected_result
        FROM audit_core.v_template_queries
        ORDER BY template_category, query_code
    """)
    with engine.connect() as conn:
        # v_template_queries already filters GROUP + active
        try:
            rows = conn.execute(sql).fetchall()
        except Exception:
            return []
    return [dict(r._mapping) for r in rows]


# ---------------------------------------------------------------------------
# Comment loader
# ---------------------------------------------------------------------------

def _load_in_review_comments(
    engine: Engine,
    category_code: str,
) -> list[dict[str, Any]]:
    """Return id + tag_name for all IN_REVIEW comments in a category."""
    sql = text("""
        SELECT id, tag_name, property_name, document_number, comment
        FROM audit_core.crs_comment
        WHERE status       = 'IN_REVIEW'
          AND category_code = :cat
          AND object_status = 'Active'
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"cat": category_code}).fetchall()
    return [dict(r._mapping) for r in rows]


# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------

def _run_group_query(
    conn: Any,
    sql_query: str,
    tag_names: list[str],
    has_parameters: bool,
) -> list[dict[str, Any]]:
    """Execute one GROUP query and return rows as list of dicts."""
    try:
        if has_parameters and tag_names:
            result = conn.execute(text(sql_query), {"tag_names": tag_names})
        else:
            result = conn.execute(text(sql_query))
        return [dict(r._mapping) for r in result.fetchall()]
    except Exception as exc:
        return [{"_error": str(exc)}]


# ---------------------------------------------------------------------------
# Per-comment evaluation
# ---------------------------------------------------------------------------

def _evaluate_comment(
    comment: dict[str, Any],
    all_rows: list[dict[str, Any]],
    strategy: str | None,
    expected_result: str | None,
    group_by_field: str | None,
) -> tuple[str, dict[str, Any]]:
    """Apply evaluation_strategy and return (validation_status, result_json).

    Group queries return rows for ALL tag_names. We first filter to only rows
    matching this comment's tag value (via group_by_field), then evaluate.
    """
    field = group_by_field or "tag_name"
    tag_val = str(comment.get(field) or comment.get("tag_name") or "")

    if tag_val and not any("_error" in r for r in all_rows):
        comment_rows = [r for r in all_rows if str(r.get(field, "")) == tag_val]
    else:
        comment_rows = all_rows  # aggregate or error: use full result set

    result_json: dict[str, Any] = {
        "rows": comment_rows[:50],  # cap to 50 rows per comment in stored JSON
        "count": len(comment_rows),
    }

    if not strategy or strategy in ("DEFERRED", "SEMANTIC"):
        return "DEFERRED", result_json

    # _error from query execution → INCONCLUSIVE
    if any("_error" in r for r in all_rows):
        return "INCONCLUSIVE", result_json

    if strategy == "COUNT_ZERO":
        # PASSED = no matching rows (problem absent)
        status = "PASSED" if len(comment_rows) == 0 else "FAILED"

    elif strategy == "FK_RESOLVED":
        # PASSED = at least one row (reference found)
        status = "PASSED" if len(comment_rows) > 0 else "FAILED"

    elif strategy == "NOT_NULL":
        if comment_rows:
            first_val = list(comment_rows[0].values())[0]
            status = "PASSED" if first_val is not None else "FAILED"
        else:
            status = "FAILED"

    elif strategy == "VALUE_MATCH":
        if comment_rows:
            first_val = str(list(comment_rows[0].values())[0])
            status = "PASSED" if first_val == (expected_result or "") else "FAILED"
        else:
            status = "FAILED"

    elif strategy == "AGGREGATE":
        if comment_rows:
            try:
                val = float(list(comment_rows[0].values())[0])
                threshold = float(expected_result) if expected_result else 0.0
                status = "PASSED" if val > threshold else "FAILED"
            except (TypeError, ValueError):
                status = "INCONCLUSIVE"
        else:
            status = "FAILED"

    else:
        status = "INCONCLUSIVE"

    return status, result_json


# ---------------------------------------------------------------------------
# DB writes
# ---------------------------------------------------------------------------

_UPSERT_VALIDATION = text("""
    INSERT INTO audit_core.crs_comment_validation
        (comment_id, validation_query_id, validation_status,
         validation_result_json, validation_timestamp, run_id)
    VALUES (:comment_id, :query_id, :status, :result_json::jsonb, now(), :run_id::uuid)
    ON CONFLICT (comment_id, validation_query_id) DO UPDATE SET
        validation_status      = EXCLUDED.validation_status,
        validation_result_json = EXCLUDED.validation_result_json,
        validation_timestamp   = now(),
        run_id                 = EXCLUDED.run_id
""")

_APPEND_QUERY_IDS = text("""
    UPDATE audit_core.crs_comment SET
        validation_query_ids = (
            SELECT ARRAY(
                SELECT DISTINCT unnest(
                    array_append(
                        COALESCE(validation_query_ids, ARRAY[]::uuid[]),
                        :query_id::uuid
                    )
                )
            )
        ),
        sync_timestamp = now()
    WHERE id = ANY(:comment_ids::uuid[])
""")


def _write_results(
    conn: Any,
    comment_rows: list[dict[str, Any]],
    query_id: str,
    run_id: str,
    dry_run: bool,
) -> int:
    """UPSERT validation results and update validation_query_ids."""
    if not comment_rows or dry_run:
        return len(comment_rows) if dry_run else 0

    validation_params = [
        {
            "comment_id": str(r["id"]),
            "query_id":   query_id,
            "status":     r["_status"],
            "result_json": json.dumps(r["_result_json"]),
            "run_id":     run_id,
        }
        for r in comment_rows
    ]
    conn.execute(_UPSERT_VALIDATION, validation_params)

    comment_ids = [str(r["id"]) for r in comment_rows]
    conn.execute(_APPEND_QUERY_IDS, {"query_id": query_id, "comment_ids": comment_ids})

    return len(validation_params)


# ---------------------------------------------------------------------------
# Prefect task
# ---------------------------------------------------------------------------

@task(name="crs-batch-validation", cache_policy=NO_CACHE, retries=2)
def run_batch_validation(
    engine: Engine,
    batch_size: int = 500,
    category_filter: str | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Run GROUP validation queries for all IN_REVIEW comments, by category.

    Args:
        engine: SQLAlchemy engine.
        batch_size: Max comments processed per write batch (default 500).
        category_filter: Restrict to one category code (e.g. 'CRS-C001').
        dry_run: Run queries but do not write to DB.

    Returns:
        Stats dict: {categories_checked, queries_run, comments_validated,
                     results_written, errors}.
    """
    logger = get_run_logger()
    run_id = str(uuid.uuid4())

    queries = _load_group_queries(engine)
    if not queries:
        logger.info("Batch validator: v_template_queries returned 0 GROUP queries — nothing to do.")
        return {"categories_checked": 0, "queries_run": 0, "comments_validated": 0,
                "results_written": 0, "errors": 0}

    if category_filter:
        queries = [q for q in queries if q["template_category"] == category_filter]

    # Unique categories from loaded queries
    categories = sorted({q["template_category"] for q in queries if q.get("template_category")})

    stats = {
        "categories_checked": 0,
        "queries_run": 0,
        "comments_validated": 0,
        "results_written": 0,
        "errors": 0,
    }

    for category in categories:
        comments = _load_in_review_comments(engine, category)
        if not comments:
            continue

        stats["categories_checked"] += 1
        tag_names = [c["tag_name"] for c in comments if c.get("tag_name")]

        category_queries = [q for q in queries if q["template_category"] == category]

        for query in category_queries:
            stats["queries_run"] += 1
            query_id = str(query["query_id"])

            try:
                with engine.connect() as read_conn:
                    all_rows = _run_group_query(
                        read_conn,
                        query["sql_query"],
                        tag_names,
                        bool(query.get("has_parameters")),
                    )

                evaluated: list[dict[str, Any]] = []
                for comment in comments:
                    status, result_json = _evaluate_comment(
                        comment,
                        all_rows,
                        query.get("evaluation_strategy"),
                        query.get("expected_result"),
                        query.get("group_by_field"),
                    )
                    evaluated.append({**comment, "_status": status, "_result_json": result_json})

                stats["comments_validated"] += len(evaluated)

                # Write in batches
                for batch_start in range(0, len(evaluated), batch_size):
                    batch = evaluated[batch_start: batch_start + batch_size]
                    with engine.begin() as write_conn:
                        written = _write_results(write_conn, batch, query_id, run_id, dry_run)
                        stats["results_written"] += written

            except Exception as exc:
                logger.error(
                    "Batch validator error — category=%s query=%s: %s",
                    category, query.get("query_code"), exc,
                )
                stats["errors"] += 1

    logger.info(
        "Batch validator complete%s: categories=%d queries=%d validated=%d written=%d errors=%d",
        " [DRY-RUN]" if dry_run else "",
        stats["categories_checked"],
        stats["queries_run"],
        stats["comments_validated"],
        stats["results_written"],
        stats["errors"],
    )
    return stats
