"""
Tier 2 keyword classifier for CRS cascade classifier.

Two-pass classification (deterministic, no DB, no LLM):
  Pass 1 — SheetRule: classify by detail_sheet name (confidence=0.95).
            Sheet names directly identify the problem type with near-certainty.
            Covers ~30-40% of Tier 2 comments.
  Pass 2 — KeywordRule: classify by regex against comment text (confidence=0.85).
            10+ patterns covering common CRS complaint categories.

Amendment #3: SheetRule runs BEFORE keyword regex as it's more deterministic.

Speed: ~200k records/sec (pure Python regex, O(n×m)).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from prefect import task, get_run_logger

# ---------------------------------------------------------------------------
# Sheet-name rules (Amendment #3 — higher confidence than keyword regex)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SheetRule:
    """Classification rule based on detail_sheet column value."""
    sheet_name: str          # substring match against detail_sheet (case-insensitive)
    category: str
    check_type: str
    confidence: float = 0.95


SHEET_RULES: list[SheetRule] = [
    SheetRule("No Doc Reference",    "MISSING_DOCUMENT_LINK",   "TAG_HAS_DOCUMENT"),
    SheetRule("No Doc Ref",          "MISSING_DOCUMENT_LINK",   "TAG_HAS_DOCUMENT"),
    SheetRule("Missing Doc",         "MISSING_DOCUMENT_LINK",   "TAG_HAS_DOCUMENT"),
    SheetRule("Tag Description",     "TAG_DESCRIPTION_ISSUE",   "TAG_EXISTS"),
    SheetRule("Spell Check",         "SPELLING_ERROR",          "TAG_EXISTS"),
    SheetRule("Spelling",            "SPELLING_ERROR",          "TAG_EXISTS"),
    SheetRule("Safety Critical",     "SAFETY_CRITICAL_MISSING", "TAG_EXISTS"),
    SheetRule("Safety_Critical",     "SAFETY_CRITICAL_MISSING", "TAG_EXISTS"),
    SheetRule("Plant Code",          "WRONG_LOCATION",          "TAG_EXISTS"),
    SheetRule("Area Code",           "WRONG_LOCATION",          "TAG_EXISTS"),
    SheetRule("From To Tag",         "MISSING_FROM_TO_LINK",    "TAG_FROM_TO_LINK"),
    SheetRule("From_To",             "MISSING_FROM_TO_LINK",    "TAG_FROM_TO_LINK"),
    SheetRule("Connection",          "MISSING_FROM_TO_LINK",    "TAG_FROM_TO_LINK"),
    SheetRule("Tag Class",           "WRONG_TAG_CLASS",         "TAG_EXISTS"),
    SheetRule("Wrong Class",         "WRONG_TAG_CLASS",         "TAG_EXISTS"),
    SheetRule("Duplicate",           "DUPLICATE_TAG",           "TAG_EXISTS"),
    SheetRule("Not Found",           "TAG_NOT_FOUND",           "TAG_EXISTS"),
    SheetRule("Missing Property",    "MISSING_PROPERTY",        "TAG_HAS_PROPERTY"),
    SheetRule("Property Missing",    "MISSING_PROPERTY",        "TAG_HAS_PROPERTY"),
]


def _classify_by_sheet(detail_sheet: str | None) -> tuple[str | None, str | None, float]:
    """Try to classify by detail_sheet name substring match.

    Returns:
        (category, check_type, confidence) or (None, None, 0.0) if no match.
    """
    if not detail_sheet:
        return None, None, 0.0
    sheet_lower = detail_sheet.lower()
    for rule in SHEET_RULES:
        if rule.sheet_name.lower() in sheet_lower:
            return rule.category, rule.check_type, rule.confidence
    return None, None, 0.0


# ---------------------------------------------------------------------------
# Keyword rules (regex-based, ordered — first match wins)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KeywordRule:
    """Classification rule based on comment text regex match."""
    pattern: re.Pattern  # type: ignore[type-arg]
    category: str
    check_type: str
    confidence: float = 0.85


KEYWORD_RULES: list[KeywordRule] = [
    # MISSING_DOCUMENT_LINK
    KeywordRule(
        re.compile(
            r"no\s+document\s+(ref(erence)?|link)"
            r"|not\s+linked\s+to\s+(any\s+)?doc"
            r"|missing\s+doc(ument)?"
            r"|document\s+(not\s+)?(linked|found|attached|present)",
            re.I,
        ),
        "MISSING_DOCUMENT_LINK", "TAG_HAS_DOCUMENT",
    ),
    # TAG_NOT_FOUND
    KeywordRule(
        re.compile(
            r"not\s+(found|present|exist(s)?|in\s+edw|in\s+(the\s+)?database)"
            r"|tag\s+(does\s+not|doesn'?t)\s+exist"
            r"|cannot\s+find\s+(tag|this)",
            re.I,
        ),
        "TAG_NOT_FOUND", "TAG_EXISTS",
    ),
    # MISSING_PROPERTY
    KeywordRule(
        re.compile(
            r"(property|attribute|field)\s+(not\s+)?(provided|missing|empty|blank|incorrect|absent)"
            r"|missing\s+(property|attribute)"
            r"|property\s+value\s+(is\s+)?(empty|blank|null|missing)",
            re.I,
        ),
        "MISSING_PROPERTY", "TAG_HAS_PROPERTY",
    ),
    # WRONG_TAG_CLASS
    KeywordRule(
        re.compile(
            r"(wrong|incorrect|invalid)\s+(tag\s+)?class"
            r"|class\s+(is\s+)?(wrong|incorrect|should\s+be)"
            r"|wrong\s+equipment\s+class",
            re.I,
        ),
        "WRONG_TAG_CLASS", "TAG_EXISTS",
    ),
    # TAG_DESCRIPTION_ISSUE
    KeywordRule(
        re.compile(
            r"(tag\s+)?description\s+(is\s+)?(missing|blank|empty|incorrect|wrong)"
            r"|description\s+not\s+provided"
            r"|missing\s+(tag\s+)?description",
            re.I,
        ),
        "TAG_DESCRIPTION_ISSUE", "TAG_EXISTS",
    ),
    # SPELLING_ERROR
    KeywordRule(
        re.compile(
            r"spell(ing)?\s+(error|mistake|check|issue)"
            r"|typo\b|mis-?spell",
            re.I,
        ),
        "SPELLING_ERROR", "TAG_EXISTS",
    ),
    # MISSING_FROM_TO_LINK
    KeywordRule(
        re.compile(
            r"(from|to)\s+tag\s+(is\s+)?(missing|blank|empty|not\s+(found|linked))"
            r"|missing\s+(from|to)\s+tag"
            r"|from[_\s]to\s+(link|tag|connection)\s+(is\s+)?(missing|not\s+set)",
            re.I,
        ),
        "MISSING_FROM_TO_LINK", "TAG_FROM_TO_LINK",
    ),
    # SAFETY_CRITICAL_MISSING
    KeywordRule(
        re.compile(
            r"safety\s+critical\s+(item\s+)?(reason|group|value|flag)?\s*(is\s+)?(missing|blank|empty)"
            r"|missing\s+safety\s+critical"
            r"|sece\s+(group\s+)?(is\s+)?(missing|blank|empty|not\s+set)",
            re.I,
        ),
        "SAFETY_CRITICAL_MISSING", "TAG_EXISTS",
    ),
    # WRONG_LOCATION (area/plant/process unit mismatch)
    KeywordRule(
        re.compile(
            r"(wrong|incorrect|invalid)\s+(plant|area|process\s+unit|location)"
            r"|(plant|area|process\s+unit)\s+(code\s+)?(is\s+)?(wrong|incorrect|should\s+be)",
            re.I,
        ),
        "WRONG_LOCATION", "TAG_EXISTS",
    ),
    # DUPLICATE_TAG
    KeywordRule(
        re.compile(
            r"duplicate\s+(tag|entry|record)"
            r"|already\s+exists?\s+in\s+(edw|database|register)"
            r"|this\s+tag\s+already\s+exists?",
            re.I,
        ),
        "DUPLICATE_TAG", "TAG_EXISTS",
    ),
    # WRONG_TAG_STATUS
    KeywordRule(
        re.compile(
            r"(wrong|incorrect|invalid)\s+(tag\s+)?status"
            r"|status\s+(is\s+)?(wrong|incorrect|should\s+be)"
            r"|tag\s+status\s+(should|must)\s+be",
            re.I,
        ),
        "WRONG_TAG_STATUS", "TAG_EXISTS",
    ),
]


def classify_by_keywords(
    text: str,
) -> tuple[str | None, str | None, float]:
    """Try to classify comment text with keyword regex rules.

    Args:
        text: Raw comment text.

    Returns:
        (category, check_type, confidence) or (None, None, 0.0) if no match.
    """
    if not text:
        return None, None, 0.0
    for rule in KEYWORD_RULES:
        if rule.pattern.search(text):
            return rule.category, rule.check_type, rule.confidence
    return None, None, 0.0


def classify_comment(
    comment: dict[str, Any],
) -> tuple[str | None, str | None, float]:
    """Classify a single comment using sheet rule first, then keywords.

    Args:
        comment: crs_comment dict with 'detail_sheet', 'comment', 'group_comment'.

    Returns:
        (category, check_type, confidence) or (None, None, 0.0) if unmatched.
    """
    # Amendment #3: sheet rule has priority (0.95 confidence vs 0.85 for keywords)
    cat, chk, conf = _classify_by_sheet(comment.get("detail_sheet"))
    if cat:
        return cat, chk, conf

    text = comment.get("comment") or comment.get("group_comment") or ""
    return classify_by_keywords(text)


# ---------------------------------------------------------------------------
# Prefect task
# ---------------------------------------------------------------------------

@task(name="tier2-keyword-classifier")
def run_tier2(
    comments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Classify comments using sheet names and keyword regex rules (Tier 2).

    No DB access. No LLM. Pure deterministic classification.

    Args:
        comments: Batch of unclassified comment dicts (passed from Tier 1).

    Returns:
        (unmatched, classified) — unmatched go to Tier 3 LLM.
    """
    logger = get_run_logger()

    unmatched: list[dict[str, Any]] = []
    classified: list[dict[str, Any]] = []
    sheet_matched = 0
    keyword_matched = 0

    for comment in comments:
        # Sheet rule first
        cat, chk, conf = _classify_by_sheet(comment.get("detail_sheet"))
        if cat:
            sheet_matched += 1
        else:
            text = comment.get("comment") or comment.get("group_comment") or ""
            cat, chk, conf = classify_by_keywords(text)
            if cat:
                keyword_matched += 1

        if cat:
            classified.append({
                **comment,
                "llm_category":            cat,
                "llm_category_confidence": conf,
                "check_type":              chk,
                "classification_tier":     2,
                "status":                  "CLASSIFIED",
            })
        else:
            unmatched.append(comment)

    logger.info(
        "Tier 2: %d classified (sheet=%d, keyword=%d), %d unmatched → Tier 3.",
        len(classified), sheet_matched, keyword_matched, len(unmatched),
    )
    return unmatched, classified
