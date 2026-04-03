"""
Tier 0 pre-filter for CRS cascade classifier.

Deterministically skips ~5-10% of comments that don't need classification:
  1. Informational phrases ("For information", "See attached", "FYI", etc.)
  2. tag_name set but tag_id is NULL (tag not in EDW)
  3. Tag has a non-active status (Inactive, ASB, VOIDED, VOIDD, CANCELLED)

Speed: ~500k records/sec (pure Python + single batch DB prefetch).
No LLM calls. No per-row queries.
"""
from __future__ import annotations

import re
from typing import Any

from prefect import task, get_run_logger
from prefect.cache_policies import NO_CACHE
from sqlalchemy.engine import Engine

from etl.tasks.crs_helpers import prefetch_tag_statuses

# ---------------------------------------------------------------------------
# Skip reason constants
# ---------------------------------------------------------------------------

SKIP_REASON_INFORMATIONAL = "INFORMATIONAL"
SKIP_REASON_TAG_NOT_IN_EDW = "TAG_NOT_IN_EDW"
SKIP_REASON_TAG_INACTIVE = "TAG_INACTIVE"

# ---------------------------------------------------------------------------
# Informational phrase pattern
# Matches comments that are status/notification notes, not actionable CRS items.
# ---------------------------------------------------------------------------

_INFO_PATTERN = re.compile(
    r"\b("
    r"for\s+information(\s+only)?"
    r"|see\s+attached"
    r"|fyi\b"
    r"|for\s+your\s+(information|review|reference|action)"
    r"|note\s*[:\-]"
    r"|please\s+note"
    r"|no\s+action\s+required"
    r"|no\s+comment"
    r"|no\s+further\s+(action|comment)"
    r"|acknowledged"
    r"|confirmed\b"
    r"|ok\b|okay\b"
    r"|noted\b"
    r"|no\s+matching\s+detail\s+sheet(\s+found)?"
    r"|please\s+find\s+(the\s+)?attached(\s+file)?"
    r"|please\s+(refer|see)\s+(the\s+)?attach(ed)?"
    r"|data\s+is\s+still\s+to\s+be\s+completed"
    r"|data\s+to\s+be\s+completed\s+in\s+next"
    r")\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Multi-comment group pattern
# Matches group_comment values that are administrative wrappers only.
# Individual comment fields in these groups hold the real defect texts.
# ---------------------------------------------------------------------------

_MULTI_COMMENT_PATTERN = re.compile(
    r"\bmultiple\s+comments[:\s]"
    r"|this\s+sheet\s+contains\s+multiple\s+comments",
    re.IGNORECASE,
)


def is_multi_comment_group(comment: dict[str, Any]) -> bool:
    """Return True if this row belongs to a 'multiple comments' wrapper group.

    Such groups use group_comment as an administrative header only.
    The actionable defect text (if any) lives in the individual comment field.

    Args:
        comment: Dict with keys from crs_comment row.

    Returns:
        True when group_comment matches the multi-comment wrapper pattern.
    """
    g = (comment.get("group_comment") or "").strip()
    return bool(_MULTI_COMMENT_PATTERN.search(g))


# ---------------------------------------------------------------------------
# Skip statuses — non-active tag states that should not be classified.
# ASB = Abandoned/Scrapped; VOIDD/VOIDED = typos seen in production xlsx.
# ---------------------------------------------------------------------------

_SKIP_STATUSES: frozenset[str] = frozenset({
    "inactive",
    "asb",
    "voided",
    "voidd",
    "cancelled",
    "void",
})


# ---------------------------------------------------------------------------
# Public helper — used by the main flow for single-comment checks
# ---------------------------------------------------------------------------

def should_skip(
    comment: dict[str, Any],
    tag_status_lookup: dict[str, str],
) -> tuple[bool, str | None]:
    """Determine if a single comment should be skipped.

    Args:
        comment: Dict with keys from crs_comment row.
        tag_status_lookup: Pre-fetched {tag_name: tag_status} dict.

    Returns:
        (True, reason) if should skip; (False, None) otherwise.
    """
    # 1. Informational / multi-comment wrapper handling
    _c = comment.get("comment")
    _g = comment.get("group_comment")
    group_text      = (_g or "").strip()
    individual_text = (_c or "").strip()

    if is_multi_comment_group(comment):
        # group_comment is an administrative wrapper — not an error signal.
        # Only skip rows where the individual comment is empty (no actionable content).
        if not individual_text:
            return True, SKIP_REASON_INFORMATIONAL
        # Non-empty individual comment → pass through to Tier 1+
        return False, None

    # Standard path: check both group_comment and individual text.
    if _INFO_PATTERN.search(group_text):
        return True, SKIP_REASON_INFORMATIONAL

    text = individual_text or group_text
    if _INFO_PATTERN.search(text):
        return True, SKIP_REASON_INFORMATIONAL

    # 2. tag_name set but tag_id is NULL → tag not resolved in EDW
    tag_name = comment.get("tag_name")
    tag_id = comment.get("tag_id")
    if tag_name and not tag_id:
        return True, SKIP_REASON_TAG_NOT_IN_EDW

    # 3. Tag has inactive/scrapped status
    if tag_name:
        status = tag_status_lookup.get(tag_name, "")
        if status and status.lower() in _SKIP_STATUSES:
            return True, SKIP_REASON_TAG_INACTIVE

    return False, None


# ---------------------------------------------------------------------------
# Prefect task
# ---------------------------------------------------------------------------

@task(name="tier0-prefilter", cache_policy=NO_CACHE)
def run_tier0(
    comments: list[dict[str, Any]],
    engine: Engine,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Skip comments that don't need classification (Tier 0).

    Skipped comments are written back with status='DEFERRED' — the only
    allowed status in crs_comment_status_check outside the RECEIVED\u2192IN_REVIEW
    pipeline.

    Args:
        comments: Batch of crs_comment dicts with status='RECEIVED'.
        engine: SQLAlchemy engine (used for single batch tag status prefetch).

    Returns:
        (to_process, skipped) — lists of comment dicts.
        Skipped dicts have extra fields: status, classification_tier, skip_reason.
    """
    logger = get_run_logger()

    # Single batch query for all tag names in this batch
    tag_names = [c["tag_name"] for c in comments if c.get("tag_name")]
    tag_status_lookup = prefetch_tag_statuses(tag_names, engine)

    to_process: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for comment in comments:
        skip, reason = should_skip(comment, tag_status_lookup)
        if skip:
            skipped.append({
                **comment,
                # DEFERRED is the correct status for informational/unresolvable comments
                # (allowed by crs_comment_status_check constraint)
                "status":              "DEFERRED",
                "llm_category":        "N/A",
                "classification_tier": 0,
                "skip_reason":         reason,
            })
        else:
            to_process.append(comment)

    logger.info(
        "Tier 0: %d skipped (informational=%d, not_in_edw=%d, inactive=%d), "
        "%d passed through.",
        len(skipped),
        sum(1 for s in skipped if s["skip_reason"] == SKIP_REASON_INFORMATIONAL),
        sum(1 for s in skipped if s["skip_reason"] == SKIP_REASON_TAG_NOT_IN_EDW),
        sum(1 for s in skipped if s["skip_reason"] == SKIP_REASON_TAG_INACTIVE),
        len(to_process),
    )
    return to_process, skipped
