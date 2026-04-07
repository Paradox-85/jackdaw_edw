"""
Tier 2.5 benchmark matcher for CRS cascade classifier.

Matches comments against curated benchmark examples (audit_core.crs_benchmark_example)
using sequence similarity. Comments with high similarity (>=0.92) to any benchmark
are classified using the benchmark's category, status, and confidence.

This is a safety net for known problematic patterns that LLM (Tier 3) consistently
misclassifies. Examples are curated from dry-run analysis and stored in the DB.

Graceful degradation: If the benchmark table does not exist or has no active rows,
the task returns all input comments as unmatched (logs WARNING). This ensures the
classifier pipeline continues to work even if the benchmark table is missing.

Speed: ~1-2k records/sec (difflib.SequenceMatcher + wildcard handling).
"""
from __future__ import annotations

import difflib
import re
from typing import Any

from prefect import task, get_run_logger
from prefect.cache_policies import NO_CACHE
from sqlalchemy import Engine, text

# Advisory voting notation (1oo2, 1oo4, etc.) is never a classifiable CRS category.
# Any benchmark match that contains this pattern must route to NEEDSNEWCATEGORY.
_ONE_OO_N_PAT = re.compile(r"1[oO][oO]\d", re.IGNORECASE)


def _normalize_comment(comment: str) -> str:
    """Normalize comment text for matching (lowercase, strip, collapse whitespace).

    Does NOT replace tags with placeholders — preserves original identifiers.
    Pattern from crs_text_generalizer.py.

    Args:
        comment: Raw comment text.

    Returns:
        Normalized text for matching.
    """
    if not comment:
        return ""
    # Lowercase, strip, collapse multiple spaces to single space
    return re.sub(r"\s+", " ", comment.lower().strip())


@task(name="tier2.5-benchmark-matcher", cache_policy=NO_CACHE)
def run_tier25_benchmark(
    comments: list[dict[str, Any]],
    engine: Engine,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Match comments against benchmark examples (Tier 2.5).

    Comments with similarity >= 0.92 to any benchmark pattern are classified.
    Uses sequence similarity (difflib.SequenceMatcher) with wildcard support
    (patterns ending with % use str.startswith()).

    Args:
        comments: Batch of unclassified comment dicts (passed from Tier 2).
        engine: SQLAlchemy engine for benchmark lookup.

    Returns:
        (unmatched, classified) — classified have benchmark-matched results,
        unmatched go to Tier 3 LLM.
    """
    logger = get_run_logger()

    # Load benchmark patterns from DB
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, comment_pattern, category, assigned_status, confidence
                FROM audit_core.crs_benchmark_example
                WHERE object_status = 'Active'
                ORDER BY id
            """))
            benchmarks = result.fetchall()

        if not benchmarks:
            logger.warning(
                "Tier 2.5: benchmark table empty or no active rows — "
                "passing all %d comments to Tier 3.",
                len(comments),
            )
            return [], comments

    except Exception as e:  # noqa: BLE001
        # Graceful degradation: table may not exist or DB error
        logger.warning(
            "Tier 2.5: benchmark table not available — %s: %s. "
            "Passing all %d comments to Tier 3.",
            type(e).__name__, e, len(comments),
        )
        return [], comments

    # Build wildcard cache (patterns ending with %)
    wildcard_patterns: list[tuple[str, Any]] = [
        (row[1][:-1], row)  # Strip trailing % for faster comparison
        for row in benchmarks
        if row[1].endswith("%")
    ]
    # Build exact-match cache (non-wildcard patterns)
    exact_patterns: list[tuple[str, Any]] = [
        (row[1], row)
        for row in benchmarks
        if not row[1].endswith("%")
    ]

    classified: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []

    for comment in comments:
        comment_text = comment.get("comment") or comment.get("group_comment") or ""
        if not comment_text:
            unmatched.append(comment)
            continue

        norm_comment = _normalize_comment(comment_text)
        matched_benchmark = None

        # Wildcard patterns: str.startswith()
        for pattern, benchmark in wildcard_patterns:
            if norm_comment.startswith(pattern):
                matched_benchmark = benchmark
                break

        # Exact patterns: SequenceMatcher ratio >= 0.92
        if not matched_benchmark:
            for pattern, benchmark in exact_patterns:
                ratio = difflib.SequenceMatcher(
                    None, norm_comment, _normalize_comment(pattern)
                ).ratio()
                if ratio >= 0.92:
                    matched_benchmark = benchmark
                    break

        if matched_benchmark:
            # Benchmark row: (id, comment_pattern, category, assigned_status, confidence)
            cat_code   = matched_benchmark[2]
            cat_conf   = float(matched_benchmark[4])
            cat_status = matched_benchmark[3]

            # Post-match guard: 1ooN (e.g. 1oo2, 1oo4) is advisory voting logic —
            # never a classifiable CRS category regardless of what the benchmark says.
            if _ONE_OO_N_PAT.search(norm_comment):
                cat_code   = "OTHER"
                cat_conf   = 0.25
                cat_status = "NEEDSNEWCATEGORY"
                logger.warning(
                    "Tier 2.5: 1ooN pattern detected — overriding benchmark match to "
                    "NEEDSNEWCATEGORY. norm_comment=%.80s", norm_comment,
                )

            classified.append({
                **comment,
                "category_code": cat_code,
                "category_confidence": cat_conf,
                "status": cat_status,
                "classification_tier": 2.5,
                "benchmark_id": matched_benchmark[0],
            })
        else:
            unmatched.append(comment)

    logger.info(
        "Tier 2.5: %d classified, %d unmatched (benchmark table has %d active rows).",
        len(classified), len(unmatched), len(benchmarks),
    )
    return unmatched, classified
