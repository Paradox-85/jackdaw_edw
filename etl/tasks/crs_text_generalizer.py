"""
Text generalizer utility for CRS cascade classifier.

Provides comment scrubbing, group-by-generalized-key, and broadcast utilities
used by Tier 2 and Tier 3 classifiers to reduce redundant evaluations.

Group-by-apply pattern:
    1. Scrub specific engineering identifiers → generic placeholders
    2. Group N raw comments into M unique templates (M << N in production)
    3. Classify once per template
    4. Broadcast result back to all rows in each group

This reduces LLM calls from O(N) to O(M) — typically 10-20x fewer calls
when bulk comments share the same underlying error pattern.
"""
from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Compiled regex patterns — source of truth for all CRS classifier modules.
# crs_tier3_llm_classifier imports these from here (one-way dependency).
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(
    r"""
    JDA-[A-Z0-9\.\-]+          |  # JDA-SB-V3C-F001
    \b[A-Z]{2,6}[0-9]{3,}\b       # HIS0163, STN0264
    """,
    re.IGNORECASE | re.VERBOSE,
)

_DOC_RE = re.compile(r"JDAW-[A-Z0-9\-]+", re.IGNORECASE)

# NOTE: _PROPERTY_RE is kept for reference / potential future use in Tier 1/2,
# but is intentionally NOT applied in generalize_comment().
# Property names (DESIGN_PRESSURE, FLUID_SERVICE, etc.) are meaningful context
# for the LLM and should be preserved in the generalised key.
# The catch-all [A-Z][A-Z0-9_]{4,} with re.IGNORECASE was destroying
# ordinary English words, producing meaningless keys.
_PROPERTY_RE = re.compile(
    r"\b(DESIGN_PRESSURE|DESIGN_TEMPERATURE|OPERATING_PRESSURE|OPERATING_TEMPERATURE"
    r"|FLUID_SERVICE|MATERIAL_GRADE|INSULATION_TYPE|HEAT_TRACING|IP_GRADE|EX_CLASS"
    r"|MANUFACTURER|SERIAL_NUMBER|MODEL_NUMBER|[A-Z][A-Z0-9_]{4,})\b",
    re.IGNORECASE,
)

# Matches standalone integers — replaced with "N" to merge "8990 tags" with "15 tags"
_INT_RE = re.compile(r"\b\d+\b")

# Trailing punctuation to strip after substitutions
_TRAILING_PUNCT_RE = re.compile(r"[,;:()\[\]]+\s*$")

# Collapse runs of whitespace to single space
_WHITESPACE_RE = re.compile(r"\s+")


def generalize_comment(text: str) -> str:
    """Scrub specific engineering identifiers from comment text.

    Produces a hashable generic template so that comments sharing the same
    error pattern (differing only in tag names, doc numbers, or counts)
    are grouped together for a single classification pass.

    Substitutions applied in priority order:
        1. Document numbers (JDAW-...) → "<DOC>"
        2. Tag names (JDA-... / alphanumeric codes) → "<TAG>"
        3. Standalone integers → "N"
        4. Strip trailing punctuation
        5. Normalise whitespace + lowercase

    Property names (DESIGN_PRESSURE, FLUID_SERVICE etc.) are intentionally
    preserved — they carry semantic meaning for the LLM classifier.

    Args:
        text: Raw comment or group_comment string.

    Returns:
        Generalised lowercase string. Empty input returns "_empty_" sentinel.

    Examples:
        >>> generalize_comment("For 8990 listed tags process unit is not defined")
        'for N listed tags process unit is not defined'
        >>> generalize_comment("JDA-SB-V3C-F001 missing DESIGN_PRESSURE value")
        '<tag> missing design_pressure value'
        >>> generalize_comment("JDAW-MEC-0042 not found in DocMaster")
        '<doc> not found in docmaster'
        >>> generalize_comment("")
        '_empty_'
    """
    if not text or not text.strip():
        return "_empty_"

    result = text

    # Doc numbers before tags — JDAW-... would also match the broad TAG pattern
    result = _DOC_RE.sub("<DOC>", result)
    result = _TAG_RE.sub("<TAG>", result)
    # _PROPERTY_RE intentionally not applied — see note above
    result = _INT_RE.sub("N", result)

    result = _TRAILING_PUNCT_RE.sub("", result)
    result = _WHITESPACE_RE.sub(" ", result).strip().lower()

    return result if result else "_empty_"


def group_by_generalized(comments: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group raw comment dicts by their generalised comment key.

    Insertion order is preserved (Python 3.7+ dict guarantee).
    Each group contains all original comment dicts that share the same
    generalised text pattern.

    Args:
        comments: List of raw comment dicts, each with a "comment" or
            "group_comment" key.

    Returns:
        Ordered dict: {generalised_key: [original_comment_dict, ...]}.
        Empty-text comments are grouped under the "_empty_" sentinel key.

    Example:
        Two comments "For 8990 listed tags..." and "For 15 listed tags..."
        → both mapped to key "for N listed tags process unit is not defined"
        → single classification needed, result broadcast to both rows.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for comment in comments:
        _c = comment.get("comment")
        _g = comment.get("group_comment")
        raw = (_c.strip() if isinstance(_c, str) and _c.strip() else None) or _g or ""
        key = generalize_comment(raw)
        if key not in groups:
            groups[key] = []
        groups[key].append(comment)
    return groups


def broadcast_result(
    groups: dict[str, list[dict[str, Any]]],
    results: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fan classification results out to all rows in each group.

    For every group key that has a matching entry in results, merges the
    classification fields on top of every original row in the group.
    Groups with no result entry are passed through unchanged.

    The merge never overwrites identity fields "id" or "comment" from the
    original row — classification fields are layered on top.

    Args:
        groups: Output of group_by_generalized().
        results: Dict mapping generalised key → classification field dict
            (e.g. {"llm_category": "CRS-C08", "confidence": 0.95, ...}).

    Returns:
        Flat list of all comment dicts with classification fields applied.
        Order matches the original insertion order within each group.
    """
    output: list[dict[str, Any]] = []
    for key, rows in groups.items():
        classification = results.get(key)
        for row in rows:
            if classification:
                # Merge: classification on top, but preserve identity fields
                merged = {**row, **classification}
                # Restore fields that must not be overwritten
                for field in ("id", "comment", "group_comment"):
                    if field in row:
                        merged[field] = row[field]
                output.append(merged)
            else:
                output.append(row)
    return output
