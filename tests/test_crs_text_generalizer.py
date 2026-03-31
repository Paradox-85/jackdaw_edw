"""Tests for crs_text_generalizer — generalize_comment, group_by_generalized, broadcast_result."""
from __future__ import annotations

import pytest

from etl.tasks.crs_text_generalizer import (
    broadcast_result,
    generalize_comment,
    group_by_generalized,
)


# ---------------------------------------------------------------------------
# generalize_comment
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    # Standalone integers → N
    (
        "For 8990 listed tags process unit is not defined",
        "for N listed tags process unit is not defined",
    ),
    # Same pattern, different integer → same generalised key
    (
        "For 15 listed tags process unit is not defined",
        "for N listed tags process unit is not defined",
    ),
    # Tag name → <TAG>
    (
        "JDA-SB-V3C-F001 missing DESIGN_PRESSURE value",
        "<tag> missing <prop> value",
    ),
    # Document number → <DOC> (must precede TAG substitution)
    (
        "JDAW-MEC-0042 not found in DocMaster",
        "<doc> not found in docmaster",
    ),
    # Property name → <PROP>
    (
        "DESIGN_PRESSURE value is incorrect",
        "<prop> value is incorrect",
    ),
    # Short alphanumeric tag (2-6 uppercase letters + 3+ digits)
    (
        "HIS0163 not in tag register",
        "<tag> not in tag register",
    ),
    # Empty string → sentinel
    ("", "_empty_"),
    # Whitespace only → sentinel
    ("   ", "_empty_"),
    # No special entities — just lowercased
    (
        "No specific entities here",
        "no specific entities here",
    ),
    # Trailing punctuation stripped
    (
        "tag is missing,",
        "tag is missing",
    ),
    # Multiple entities in one string
    (
        "JDA-PP-P001 document JDAW-ME-E-SP-0001 not linked",
        "<tag> document <doc> not linked",
    ),
])
def test_generalize_comment(raw: str, expected: str) -> None:
    assert generalize_comment(raw) == expected


def test_generalize_comment_same_key_for_different_numbers() -> None:
    """Two comments with same pattern but different counts → identical key."""
    key1 = generalize_comment("For 8990 listed tags process unit is not defined")
    key2 = generalize_comment("For 15 listed tags process unit is not defined")
    assert key1 == key2


def test_generalize_comment_doc_before_tag() -> None:
    """JDAW-... document pattern must NOT be mangled by TAG_RE first."""
    result = generalize_comment("JDAW-ME-E-SP-0001 is missing")
    assert result == "<doc> is missing"
    assert "<tag>" not in result


# ---------------------------------------------------------------------------
# group_by_generalized
# ---------------------------------------------------------------------------

def test_group_by_generalized_deduplicates() -> None:
    """Two comments with same generalised pattern → single group."""
    comments = [
        {"id": "a", "comment": "For 8990 listed tags process unit is not defined"},
        {"id": "b", "comment": "For 15 listed tags process unit is not defined"},
        {"id": "c", "comment": "JDA-SB-V3C-F001 missing DESIGN_PRESSURE value"},
    ]
    groups = group_by_generalized(comments)
    assert len(groups) == 2, "Expected 2 unique templates"


def test_group_by_generalized_preserves_order() -> None:
    """Insertion order of groups is preserved (Python 3.7+ dict)."""
    comments = [
        {"comment": "tag JDA-PP-P001 not found"},
        {"comment": "tag JDA-PP-P002 not found"},
        {"comment": "document JDAW-ME-E-001 is missing"},
    ]
    groups = group_by_generalized(comments)
    keys = list(groups.keys())
    # First two map to the same tag pattern, last to doc pattern
    assert len(keys) == 2
    assert "<doc>" in keys[1] or "doc" in keys[1]


def test_group_by_generalized_empty_comment_sentinel() -> None:
    """Comments with no text are grouped under _empty_ sentinel."""
    comments = [{"comment": ""}, {"group_comment": "   "}, {"comment": None}]
    groups = group_by_generalized(comments)
    assert "_empty_" in groups
    assert len(groups["_empty_"]) == 3


def test_group_by_generalized_fallback_to_group_comment() -> None:
    """Falls back to group_comment when comment key is absent."""
    c = {"group_comment": "JDA-SB-V3C-F001 not in register"}
    groups = group_by_generalized([c])
    assert len(groups) == 1
    key = next(iter(groups))
    assert "<tag>" in key


def test_group_by_generalized_single_item_groups() -> None:
    """Unique comments each form their own group."""
    comments = [
        {"comment": "tag is missing"},
        {"comment": "document not found"},
        {"comment": "property is blank"},
    ]
    groups = group_by_generalized(comments)
    assert len(groups) == 3
    for rows in groups.values():
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# broadcast_result
# ---------------------------------------------------------------------------

def test_broadcast_result_applies_to_all_rows() -> None:
    """Classification result is merged onto every row in the group."""
    groups = {
        "for N listed tags process unit is not defined": [
            {"id": "uuid-1", "comment": "For 8990 listed tags process unit is not defined"},
            {"id": "uuid-2", "comment": "For 15 listed tags process unit is not defined"},
        ]
    }
    results = {
        "for N listed tags process unit is not defined": {
            "category": "CRS-C08",
            "confidence": 0.95,
        }
    }
    rows = broadcast_result(groups, results)
    assert len(rows) == 2
    assert all(r["category"] == "CRS-C08" for r in rows)
    assert all(r["confidence"] == 0.95 for r in rows)


def test_broadcast_result_preserves_identity_fields() -> None:
    """id and comment fields from original row are NOT overwritten."""
    groups = {
        "key": [
            {"id": "uuid-1", "comment": "For 8990 listed tags process unit is not defined"},
            {"id": "uuid-2", "comment": "For 15 listed tags process unit is not defined"},
        ]
    }
    results = {
        "key": {"id": "WRONG_ID", "comment": "WRONG_COMMENT", "category": "CRS-C08"}
    }
    rows = broadcast_result(groups, results)
    assert rows[0]["id"] == "uuid-1"
    assert rows[0]["comment"] == "For 8990 listed tags process unit is not defined"
    assert rows[1]["id"] == "uuid-2"


def test_broadcast_result_passthrough_for_missing_key() -> None:
    """Groups with no matching result entry are returned unchanged."""
    groups = {
        "matched_key": [{"id": "a", "comment": "matched"}],
        "unmatched_key": [{"id": "b", "comment": "unmatched"}],
    }
    results = {"matched_key": {"category": "CRS-C01"}}
    rows = broadcast_result(groups, results)
    assert len(rows) == 2
    matched = next(r for r in rows if r["id"] == "a")
    unmatched = next(r for r in rows if r["id"] == "b")
    assert matched["category"] == "CRS-C01"
    assert "category" not in unmatched


def test_broadcast_result_empty_groups() -> None:
    """Empty groups dict returns empty list without error."""
    assert broadcast_result({}, {}) == []


def test_broadcast_result_empty_results() -> None:
    """When results is empty, all rows pass through unchanged."""
    groups = {"key": [{"id": "x", "comment": "text"}]}
    rows = broadcast_result(groups, {})
    assert rows == [{"id": "x", "comment": "text"}]


def test_broadcast_result_output_length_matches_input() -> None:
    """Total output rows == total input rows across all groups."""
    comments = [{"id": str(i), "comment": f"tag JDA-PP-P{i:03d} not found"} for i in range(10)]
    groups = group_by_generalized(comments)
    results = {key: {"category": "CRS-C11"} for key in groups}
    rows = broadcast_result(groups, results)
    assert len(rows) == 10
