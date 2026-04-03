"""
Multi-comment group detection helper for CRS cascade classifier.

This module is intentionally dependency-free (stdlib only) so it can be
imported by any module in the etl.tasks package without risk of circular
imports.

Background
----------
Some CRS reviewer sheets contain multiple unrelated defect comments on a
single row. The reviewer signals this by setting group_comment to a wrapper
phrase such as::

    "Multiple Comments: This sheet contains multiple comments,
     please check and correct."

In these cases group_comment carries no classification signal — the real
defect text lives in the individual comment field of each child row.
This module provides a single predicate to detect such wrapper groups so
that Tier 0 and the text generaliser can route them correctly.
"""
from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Pattern — matches group_comment values that are administrative wrappers.
# Kept intentionally narrow: only the two known production phrases.
# Do NOT merge into _INFO_PATTERN — these groups need special routing,
# not blanket DEFERRED treatment.
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
    Rows with an empty individual comment should be DEFERRED (no content).
    Rows with a non-empty individual comment should be classified normally
    using that comment text — group_comment must be ignored as a signal.

    Args:
        comment: Dict with keys from crs_comment row.
                 Must contain a 'group_comment' key (may be None/empty).

    Returns:
        True when group_comment matches the multi-comment wrapper pattern.

    Examples:
        >>> is_multi_comment_group({"group_comment": "Multiple Comments: This sheet contains..."})
        True
        >>> is_multi_comment_group({"group_comment": "Tag description is too short"})
        False
        >>> is_multi_comment_group({"group_comment": None})
        False
    """
    g = (comment.get("group_comment") or "").strip()
    return bool(_MULTI_COMMENT_PATTERN.search(g))
