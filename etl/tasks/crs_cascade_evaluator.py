"""
Phase 3 CRS Cascade Evaluator.

Reads validation results from audit_core.v_crs_resolution_report and generates
formal_response for IN_REVIEW comments that have been batch-validated.

Placeholder substitution in response_template:
  {tag_name}        → crs_comment.tag_name
  {property_name}   → crs_comment.property_name
  {document_number} → crs_comment.document_number
  {actual_value}    → validation_result_json['actual_value'] (if present)
  {expected_result} → crs_validation_query.expected_result

Algorithm:
  1. Load IN_REVIEW comments with validation results from v_crs_resolution_report.
  2. Group validation rows by comment_id.
  3. For each comment:
     - All validations PASSED  → fill formal_response from first PASSED template.
     - Any validation FAILED   → fill formal_response_rationale with failure info.
     - All DEFERRED/INCONCLUSIVE → skip (Phase 4 / manual review).
  4. Batch-UPDATE crs_comment.
"""
from __future__ import annotations

import re
from typing import Any

from prefect import get_run_logger, task
from prefect.cache_policies import NO_CACHE
from sqlalchemy import text
from sqlalchemy.engine import Engine


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_validation_results(engine: Engine) -> list[dict[str, Any]]:
    """Fetch all IN_REVIEW comments with at least one non-null validation result."""
    sql = text("""
        SELECT
            comment_id,
            comment_ref,
            tag_name,
            comment_status,
            category_code,
            classification_tier,
            formal_response,
            validation_status,
            validation_result_json,
            validation_error,
            query_code,
            evaluation_strategy,
            response_template,
            group_by_field,
            expected_result
        FROM audit_core.v_crs_resolution_report
        WHERE comment_status   = 'IN_REVIEW'
          AND validation_status IS NOT NULL
        ORDER BY comment_id, query_code
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r._mapping) for r in rows]


def _load_comment_details(
    engine: Engine,
    comment_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Fetch property_name and document_number for placeholder substitution."""
    if not comment_ids:
        return {}
    sql = text("""
        SELECT id, tag_name, property_name, document_number
        FROM audit_core.crs_comment
        WHERE id = ANY(:ids::uuid[])
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"ids": comment_ids}).fetchall()
    return {str(r.id): dict(r._mapping) for r in rows}


# ---------------------------------------------------------------------------
# Placeholder substitution
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def _substitute(
    template: str,
    comment: dict[str, Any],
    validation_result_json: dict[str, Any] | None,
    expected_result: str | None,
) -> str:
    """Replace {placeholder} tokens in response_template with actual values.

    Args:
        template: Response template string with {placeholder} tokens.
        comment: crs_comment dict (tag_name, property_name, document_number, …).
        validation_result_json: JSONB result from the validation query.
        expected_result: Expected result string from crs_validation_query.

    Returns:
        Substituted string; unknown placeholders are left as-is.
    """
    result_data: dict[str, Any] = {}
    if isinstance(validation_result_json, dict):
        rows = validation_result_json.get("rows", [])
        if rows and isinstance(rows[0], dict):
            result_data = rows[0]

    def _replace(m: re.Match) -> str:  # type: ignore[type-arg]
        key = m.group(1)
        if key == "tag_name":
            return comment.get("tag_name") or ""
        if key == "property_name":
            return comment.get("property_name") or ""
        if key == "document_number":
            return comment.get("document_number") or ""
        if key == "actual_value":
            return str(result_data.get("actual_value", result_data.get("value", "")))
        if key == "expected_result":
            return expected_result or ""
        # Pass unknown placeholders through unchanged
        return m.group(0)

    return _PLACEHOLDER_RE.sub(_replace, template)


# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------

def _evaluate_comment_group(
    rows: list[dict[str, Any]],
    comment_detail: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Determine formal_response and formal_response_rationale for one comment.

    Args:
        rows: All v_crs_resolution_report rows for this comment_id.
        comment_detail: crs_comment fields (property_name, document_number, …).

    Returns:
        (formal_response, formal_response_rationale) — at most one is non-None.
    """
    statuses = {r["validation_status"] for r in rows}

    # Skip if no actionable statuses (all PENDING or null)
    actionable = statuses - {"PENDING", None}
    if not actionable:
        return None, None

    # All DEFERRED or INCONCLUSIVE → leave for manual / Phase 4
    if actionable <= {"DEFERRED", "INCONCLUSIVE"}:
        return None, None

    passed_rows = [r for r in rows if r["validation_status"] == "PASSED"]
    failed_rows = [r for r in rows if r["validation_status"] == "FAILED"]

    if passed_rows and not failed_rows:
        # All validations passed → generate formal response
        template = passed_rows[0].get("response_template") or ""
        if template:
            formal_response = _substitute(
                template,
                comment_detail,
                passed_rows[0].get("validation_result_json"),
                passed_rows[0].get("expected_result"),
            )
        else:
            formal_response = (
                f"Validation passed for {comment_detail.get('tag_name', 'tag')} "
                f"(query: {passed_rows[0].get('query_code', 'N/A')})."
            )
        return formal_response, None

    if failed_rows:
        # At least one validation failed → generate rationale
        failed_codes = ", ".join(r.get("query_code", "?") for r in failed_rows)
        tag = comment_detail.get("tag_name") or "tag"
        rationale = f"Validation failed for {tag}: {failed_codes}."
        return None, rationale

    return None, None


# ---------------------------------------------------------------------------
# DB write
# ---------------------------------------------------------------------------

_UPDATE_RESPONDED = text("""
    UPDATE audit_core.crs_comment SET
        formal_response           = :response,
        formal_response_rationale = NULL,
        sync_timestamp            = now()
    WHERE id = :id
""")

_UPDATE_RATIONALE = text("""
    UPDATE audit_core.crs_comment SET
        formal_response           = NULL,
        formal_response_rationale = :rationale,
        sync_timestamp            = now()
    WHERE id = :id
""")


# ---------------------------------------------------------------------------
# Prefect task
# ---------------------------------------------------------------------------

@task(name="crs-cascade-evaluation", cache_policy=NO_CACHE, retries=2)
def evaluate_validation_results(
    engine: Engine,
    dry_run: bool = False,
) -> dict[str, int]:
    """Generate formal_response for validated IN_REVIEW comments.

    Reads audit_core.v_crs_resolution_report (comments with validation results).
    Writes formal_response / formal_response_rationale to audit_core.crs_comment.

    Args:
        engine: SQLAlchemy engine.
        dry_run: Evaluate but do not write to DB.

    Returns:
        Stats dict: {evaluated, responded, rationale_set, deferred, errors}.
    """
    logger = get_run_logger()

    rows = _load_validation_results(engine)
    if not rows:
        logger.info("Cascade evaluator: no IN_REVIEW comments with validation results — nothing to do.")
        return {"evaluated": 0, "responded": 0, "rationale_set": 0, "deferred": 0, "errors": 0}

    # Group by comment_id
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        cid = str(row["comment_id"])
        grouped.setdefault(cid, []).append(row)

    # Load comment detail for placeholder substitution
    comment_details = _load_comment_details(engine, list(grouped.keys()))

    stats = {"evaluated": 0, "responded": 0, "rationale_set": 0, "deferred": 0, "errors": 0}

    responded_params: list[dict[str, Any]] = []
    rationale_params: list[dict[str, Any]] = []

    for comment_id, comment_rows in grouped.items():
        stats["evaluated"] += 1
        detail = comment_details.get(comment_id, {
            "tag_name": comment_rows[0].get("tag_name"),
            "property_name": None,
            "document_number": None,
        })

        try:
            response, rationale = _evaluate_comment_group(comment_rows, detail)
        except Exception as exc:
            logger.error("Cascade evaluator error — comment_id=%s: %s", comment_id, exc)
            stats["errors"] += 1
            continue

        if response is not None:
            stats["responded"] += 1
            responded_params.append({"id": comment_id, "response": response})
        elif rationale is not None:
            stats["rationale_set"] += 1
            rationale_params.append({"id": comment_id, "rationale": rationale})
        else:
            stats["deferred"] += 1

    if not dry_run:
        if responded_params:
            with engine.begin() as conn:
                conn.execute(_UPDATE_RESPONDED, responded_params)
        if rationale_params:
            with engine.begin() as conn:
                conn.execute(_UPDATE_RATIONALE, rationale_params)

    logger.info(
        "Cascade evaluator complete%s: evaluated=%d responded=%d rationale=%d deferred=%d errors=%d",
        " [DRY-RUN]" if dry_run else "",
        stats["evaluated"],
        stats["responded"],
        stats["rationale_set"],
        stats["deferred"],
        stats["errors"],
    )
    return stats
