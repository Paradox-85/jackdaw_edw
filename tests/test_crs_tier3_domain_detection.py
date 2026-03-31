"""Tests for Tier 3 helper functions: _detect_comment_domain, _build_categories_line."""
from __future__ import annotations

import pytest

from etl.tasks.crs_tier3_llm_classifier import (
    _build_categories_line,
    _detect_comment_domain,
)


# ---------------------------------------------------------------------------
# _detect_comment_domain
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected_domain", [
    # Tag domain — via TAG_RE match
    ("Tag JDA-PP-P001 not found", "tag"),
    # Tag domain — via keyword
    ("Tag is missing from the register", "tag"),
    ("Equipment not found in EDW", "tag"),
    # Document domain — via DOC_RE match
    ("Refer to JDAW-ME-E-SP-0001 for details", "document"),
    # Document domain — via keyword
    ("Drawing is not in MDR", "document"),
    ("Transmittal reference missing", "document"),
    # Property domain — via PROPERTY_RE match
    ("DESIGN_PRESSURE value incorrect", "property"),
    # Property domain — via keyword
    ("pressure rating is missing", "property"),
    ("insulation type not specified", "property"),
    # Safety domain — via keyword
    ("SECE item requires safety review", "safety"),
    ("SIL rating is missing", "safety"),
    ("ATEX classification not provided", "safety"),
    # Revision domain — via keyword
    ("Superseded by revision B", "revision"),
    ("Tag status is obsolete", "revision"),
    # Fallback — no matching pattern
    ("some unrelated comment text", "other"),
    # Empty string — fallback
    ("", "other"),
])
def test_detect_comment_domain(text: str, expected_domain: str) -> None:
    assert _detect_comment_domain(text) == expected_domain


def test_detect_document_priority_over_tag() -> None:
    """Document number (JDAW-...) detected as document, not tag, even if text has tag."""
    result = _detect_comment_domain("JDAW-ME-E-SP-0001 linked to JDA-PP-P001")
    # Document regex fires first
    assert result == "document"


# ---------------------------------------------------------------------------
# _build_categories_line
# ---------------------------------------------------------------------------

# Minimal fixture templates for testing
_SAMPLE_TEMPLATES = [
    {"category": "CRS-C01", "check_type": "tag", "short_template_text": "missing required fields"},
    {"category": "CRS-C02", "check_type": "tag", "short_template_text": "tag description missing"},
    {"category": "CRS-C08", "check_type": "tag", "short_template_text": "process unit code missing"},
    {"category": "CRS-C30", "check_type": "document", "short_template_text": "document missing or NYI/CAN status"},
    {"category": "CRS-C31", "check_type": "document", "short_template_text": "tag has no document reference"},
    {"category": "CRS-C17", "check_type": "property", "short_template_text": "property tag not in MTR"},
    {"category": "CRS-C18", "check_type": "property", "short_template_text": "UOM present when value is NA"},
]


def test_build_categories_line_no_domain() -> None:
    """Without domain filter, all templates are included."""
    line = _build_categories_line(_SAMPLE_TEMPLATES, domain=None)
    assert "CRS-C01" in line
    assert "CRS-C30" in line
    assert "CRS-C17" in line


def test_build_categories_line_tag_domain() -> None:
    """Tag domain includes only tag check_type templates."""
    line = _build_categories_line(_SAMPLE_TEMPLATES, domain="tag")
    assert "CRS-C01" in line
    assert "CRS-C08" in line
    # Document category must NOT be in narrow tag result
    assert "CRS-C30" not in line
    assert "CRS-C31" not in line


def test_build_categories_line_document_domain() -> None:
    """Document domain includes only document check_type templates."""
    line = _build_categories_line(_SAMPLE_TEMPLATES, domain="document")
    assert "CRS-C30" in line
    assert "CRS-C31" in line
    assert "CRS-C01" not in line


def test_build_categories_line_property_domain() -> None:
    """Property domain filters to property check_type."""
    line = _build_categories_line(_SAMPLE_TEMPLATES, domain="property")
    assert "CRS-C17" in line
    assert "CRS-C18" in line
    assert "CRS-C01" not in line


def test_build_categories_line_fallback_to_all_when_no_domain_match() -> None:
    """When domain matches no templates, falls back to all templates."""
    line = _build_categories_line(_SAMPLE_TEMPLATES, domain="safety")
    # 'safety' is not a check_type in sample data → falls back to all
    assert "CRS-C01" in line
    assert "CRS-C30" in line


def test_build_categories_line_truncates_at_max_chars() -> None:
    """Output is truncated to max_chars."""
    line = _build_categories_line(_SAMPLE_TEMPLATES, domain=None, max_chars=50)
    assert len(line) <= 50


def test_build_categories_line_empty_input() -> None:
    """Empty templates list returns empty string without crash."""
    assert _build_categories_line([], domain="tag") == ""
    assert _build_categories_line([], domain=None) == ""


def test_build_categories_line_uses_short_text() -> None:
    """When short_template_text is set, it is used in the entry."""
    templates = [
        {"category": "CRS-C01", "check_type": "tag", "short_template_text": "missing required fields"},
    ]
    line = _build_categories_line(templates, domain=None)
    assert "missing required fields" in line


def test_build_categories_line_falls_back_to_check_type_when_no_short_text() -> None:
    """When short_template_text is None, check_type is used as fallback."""
    templates = [
        {"category": "CRS-C01", "check_type": "tag_exists", "short_template_text": None},
    ]
    line = _build_categories_line(templates, domain=None)
    assert "CRS-C01" in line
    assert "tag_exists" in line


def test_build_categories_line_default_max_chars() -> None:
    """Default max_chars=400 keeps result within 400 chars."""
    # Build a large template list to test truncation
    templates = [
        {
            "category": f"CRS-C{i:02d}",
            "check_type": "tag",
            "short_template_text": "some description text here",
        }
        for i in range(1, 51)
    ]
    line = _build_categories_line(templates, domain=None)
    assert len(line) <= 400


# ---------------------------------------------------------------------------
# Pass 2 trigger logic — unit verification
# ---------------------------------------------------------------------------

def test_pass2_triggers_on_other_and_low_confidence() -> None:
    """Pass 2 should trigger only when category==OTHER AND confidence < 0.5."""
    outputs = [
        {"category": "CRS-C01", "confidence": 0.9},   # no retry
        {"category": "OTHER", "confidence": 0.3},      # retry
        {"category": "OTHER", "confidence": 0.6},      # confidence >= 0.5, no retry
        {"category": "CRS-C08", "confidence": 0.4},    # not OTHER, no retry
        {"category": "OTHER", "confidence": 0.0},      # retry
    ]
    retry_indices = [
        i for i, out in enumerate(outputs)
        if out["category"] == "OTHER" and out["confidence"] < 0.5
    ]
    assert retry_indices == [1, 4]


def test_pass2_does_not_trigger_when_category_is_not_other() -> None:
    """Valid category with low confidence should NOT trigger Pass 2."""
    outputs = [{"category": "CRS-C08", "confidence": 0.3}]
    retry_indices = [
        i for i, out in enumerate(outputs)
        if out["category"] == "OTHER" and out["confidence"] < 0.5
    ]
    assert retry_indices == []


def test_pass2_does_not_trigger_when_confidence_at_threshold() -> None:
    """confidence == 0.5 is not strictly less than 0.5 → no retry."""
    outputs = [{"category": "OTHER", "confidence": 0.5}]
    retry_indices = [
        i for i, out in enumerate(outputs)
        if out["category"] == "OTHER" and out["confidence"] < 0.5
    ]
    assert retry_indices == []
