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
from prefect.cache_policies import NO_CACHE

from etl.tasks.crs_text_generalizer import broadcast_result, group_by_generalized

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
    category_code: str | None = None


SHEET_RULES: list[SheetRule] = [
    # MISSING_DOCUMENT_LINK → GEN-036
    SheetRule("No Doc Reference",    "MISSING_DOCUMENT_LINK",   "TAG_HAS_DOCUMENT",  category_code="GEN-036"),
    SheetRule("No Doc Ref",          "MISSING_DOCUMENT_LINK",   "TAG_HAS_DOCUMENT",  category_code="GEN-036"),
    SheetRule("Missing Doc",         "MISSING_DOCUMENT_LINK",   "TAG_HAS_DOCUMENT",  category_code="GEN-036"),

    # TAG_DESCRIPTION_ISSUE → GEN-034
    SheetRule("Tag Description",     "TAG_DESCRIPTION_ISSUE",   "TAG_EXISTS",        category_code="GEN-034"),

    # SPELLING_ERROR → GEN-008 (no CRS-Cxx equivalent existed)
    SheetRule("Spell Check",         "SPELLING_ERROR",          "TAG_EXISTS",        category_code="GEN-008"),
    SheetRule("Spelling",            "SPELLING_ERROR",          "TAG_EXISTS",        category_code="GEN-008"),

    # SAFETY_CRITICAL_MISSING → GEN-025
    SheetRule("Safety Critical",     "SAFETY_CRITICAL_MISSING", "TAG_EXISTS",        category_code="GEN-025"),
    SheetRule("Safety_Critical",     "SAFETY_CRITICAL_MISSING", "TAG_EXISTS",        category_code="GEN-025"),

    # WRONG_LOCATION → GEN-020
    SheetRule("Plant Code",          "WRONG_LOCATION",          "TAG_EXISTS",        category_code="GEN-020"),
    SheetRule("Area Code",           "WRONG_LOCATION",          "TAG_EXISTS",        category_code="GEN-020"),

    # MISSING_FROM_TO_LINK → GEN-003
    SheetRule("From To Tag",         "MISSING_FROM_TO_LINK",    "TAG_FROM_TO_LINK",  category_code="GEN-003"),
    SheetRule("From_To",             "MISSING_FROM_TO_LINK",    "TAG_FROM_TO_LINK",  category_code="GEN-003"),
    SheetRule("Connection",          "MISSING_FROM_TO_LINK",    "TAG_FROM_TO_LINK",  category_code="GEN-003"),

    # WRONG_TAG_CLASS → GEN-019
    SheetRule("Tag Class",           "WRONG_TAG_CLASS",         "TAG_EXISTS",        category_code="GEN-019"),
    SheetRule("Wrong Class",         "WRONG_TAG_CLASS",         "TAG_EXISTS",        category_code="GEN-019"),

    # DUPLICATE_TAG → GEN-006
    SheetRule("Duplicate",           "DUPLICATE_TAG",           "TAG_EXISTS",        category_code="GEN-006"),

    # TAG_NOT_FOUND → GEN-005
    SheetRule("Not Found",           "TAG_NOT_FOUND",           "TAG_EXISTS",        category_code="GEN-005"),

    # MISSING_PROPERTY → GEN-037
    SheetRule("Missing Property",    "MISSING_PROPERTY",        "TAG_HAS_PROPERTY",  category_code="GEN-037"),
    SheetRule("Property Missing",    "MISSING_PROPERTY",        "TAG_HAS_PROPERTY",  category_code="GEN-037"),

    # WRONG_TAG_STATUS → GEN-012 (REF_STATUS_INVALID)
    SheetRule("Wrong Status",        "WRONG_TAG_STATUS",        "TAG_EXISTS",        category_code="GEN-012"),
]


def _classify_by_sheet(detail_sheet: str | None) -> tuple[str | None, str | None, float, str | None]:
    """Try to classify by detail_sheet name substring match.

    Returns:
        (category, check_type, confidence, category_code) or (None, None, 0.0, None) if no match.
    """
    if not detail_sheet:
        return None, None, 0.0, None
    sheet_lower = detail_sheet.lower()
    for rule in SHEET_RULES:
        if rule.sheet_name.lower() in sheet_lower:
            return rule.category, rule.check_type, rule.confidence, rule.category_code
    return None, None, 0.0, None


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
    category_code: str | None = None


KEYWORD_RULES: list[KeywordRule] = [
    # NEW RULE 1: DOC_REF_NOT_MATCHED → GEN-036 (placed FIRST for highest priority)
    KeywordRule(
        re.compile(
            r"not\s+matched\s+with\s+\d+[_\s]doc[_\s]ref"
            r"|not\s+matched\s+with\s+\d+_doc_ref_to"
            r"|\d+_doc_ref_to_\w+",
            re.I,
        ),
        "DOC_REF_NOT_MATCHED", "TAG_HAS_DOCUMENT", category_code="GEN-036",
    ),

    # NEW RULE 2: DESC_TOO_SHORT → GEN-010
    KeywordRule(
        re.compile(
            r"(description|desc)\s+is\s+too\s+short"
            r"|too\s+short.{0,30}(description|desc)"
            r"|provide\s+a\s+more\s+detailed\s+description",
            re.I,
        ),
        "DESC_TOO_SHORT", "TAG_EXISTS", category_code="GEN-010",
    ),

    # NEW RULE 3: PLACEHOLDER_VALUE → GEN-002
    KeywordRule(
        re.compile(
            r'(code|value|field|unit|area|class|number|type)\s+is\s+(as\s+)?"?(?:NA|N/A|TBC|NONE|TBD)"?'
            r'|is\s+set\s+to\s+(?:NA|N/A|TBC|NONE|TBD)\b'
            r'|\bvalue\s+(?:NA|N/A|TBC)\b',
            re.I,
        ),
        "PLACEHOLDER_VALUE", "TAG_EXISTS", category_code="GEN-002",
    ),

    # EXISTING RULES (update crs_code → category_code):

    # MISSING_DOCUMENT_LINK → GEN-036
    KeywordRule(
        re.compile(
            r"no\s+document\s+(ref(erence)?|link)"
            r"|not\s+linked\s+to\s+(any\s+)?doc"
            r"|missing\s+doc(ument)?"
            r"|document\s+(not\s+)?(linked|found|attached|present)",
            re.I,
        ),
        "MISSING_DOCUMENT_LINK", "TAG_HAS_DOCUMENT", category_code="GEN-036",
    ),
    # TAG_NOT_FOUND → GEN-005
    KeywordRule(
        re.compile(
            r"not\s+(found|present|exist(s)?|in\s+edw|in\s+(the\s+)?database)"
            r"|tag\s+(does\s+not|doesn'?t)\s+exist"
            r"|cannot\s+find\s+(tag|this)",
            re.I,
        ),
        "TAG_NOT_FOUND", "TAG_EXISTS", category_code="GEN-005",
    ),
    # MISSING_PROPERTY → GEN-037
    KeywordRule(
        re.compile(
            r"(property|attribute|field)\s+(not\s+)?(provided|missing|empty|blank|incorrect|absent)"
            r"|missing\s+(property|attribute)"
            r"|property\s+value\s+(is\s+)?(empty|blank|null|missing)",
            re.I,
        ),
        "MISSING_PROPERTY", "TAG_HAS_PROPERTY", category_code="GEN-037",
    ),
    # WRONG_TAG_CLASS → GEN-019
    KeywordRule(
        re.compile(
            r"(wrong|incorrect|invalid)\s+(tag\s+)?class"
            r"|class\s+(is\s+)?(wrong|incorrect|should\s+be)"
            r"|wrong\s+equipment\s+class",
            re.I,
        ),
        "WRONG_TAG_CLASS", "TAG_EXISTS", category_code="GEN-019",
    ),
    # TAG_DESCRIPTION_ISSUE → GEN-034
    KeywordRule(
        re.compile(
            r"(tag\s+)?description\s+(is\s+)?(missing|blank|empty|incorrect|wrong)"
            r"|description\s+not\s+provided"
            r"|missing\s+(tag\s+)?description",
            re.I,
        ),
        "TAG_DESCRIPTION_ISSUE", "TAG_EXISTS", category_code="GEN-034",
    ),
    # SPELLING_ERROR → GEN-008
    KeywordRule(
        re.compile(
            r"spell(ing)?\s+(error|mistake|check|issue)"
            r"|typo\b|mis-?spell",
            re.I,
        ),
        "SPELLING_ERROR", "TAG_EXISTS", category_code="GEN-008",
    ),
    # MISSING_FROM_TO_LINK → GEN-003
    KeywordRule(
        re.compile(
            r"(from|to)\s+tag\s+(is\s+)?(missing|blank|empty|not\s+(found|linked))"
            r"|missing\s+(from|to)\s+tag"
            r"|from[_\s]to\s+(link|tag|connection)\s+(is\s+)?(missing|not\s+set)",
            re.I,
        ),
        "MISSING_FROM_TO_LINK", "TAG_FROM_TO_LINK", category_code="GEN-003",
    ),
    # SAFETY_CRITICAL_MISSING → GEN-025
    KeywordRule(
        re.compile(
            r"safety\s+critical\s+(item\s+)?(reason|group|value|flag)?\s*(is\s+)?(missing|blank|empty)"
            r"|missing\s+safety\s+critical"
            r"|sece\s+(group\s+)?(is\s+)?(missing|blank|empty|not\s+set)",
            re.I,
        ),
        "SAFETY_CRITICAL_MISSING", "TAG_EXISTS", category_code="GEN-025",
    ),
    # WRONG_LOCATION → GEN-020
    KeywordRule(
        re.compile(
            r"(wrong|incorrect|invalid)\s+(plant|area|process\s+unit|location)"
            r"|(plant|area|process\s+unit)\s+(code\s+)?(is\s+)?(wrong|incorrect|should\s+be)",
            re.I,
        ),
        "WRONG_LOCATION", "TAG_EXISTS", category_code="GEN-020",
    ),
    # DUPLICATE_TAG → GEN-006
    KeywordRule(
        re.compile(
            r"duplicate\s+(tag|entry|record)"
            r"|already\s+exists?\s+in\s+(edw|database|register)"
            r"|this\s+tag\s+already\s+exists?",
            re.I,
        ),
        "DUPLICATE_TAG", "TAG_EXISTS", category_code="GEN-006",
    ),
    # WRONG_TAG_STATUS → GEN-012 (REF_STATUS_INVALID)
    KeywordRule(
        re.compile(
            r"(wrong|incorrect|invalid)\s+(tag\s+)?status"
            r"|status\s+(is\s+)?(wrong|incorrect|should\s+be)"
            r"|tag\s+status\s+(should|must)\s+be",
            re.I,
        ),
        "WRONG_TAG_STATUS", "TAG_EXISTS", category_code="GEN-012",
    ),
]


# Module-level validation: accepts both GEN-xxx and CRS-Cxxx formats
_all_tier2_codes = [r.category_code for r in SHEET_RULES + KEYWORD_RULES if r.category_code]
_valid_gen = re.compile(r"^GEN-\d{3}$")
_valid_crs = re.compile(r"^CRS-C\d{3}$")
_invalid = [
    c for c in _all_tier2_codes
    if not (_valid_gen.match(c) or _valid_crs.match(c))
]
assert not _invalid, (
    f"Invalid category codes in Tier 2 rules (must be GEN-NNN or CRS-CNNN): {_invalid}"
)


def classify_by_keywords(
    text: str,
) -> tuple[str | None, str | None, float, str | None]:
    """Try to classify comment text with keyword regex rules.

    Args:
        text: Raw comment text.

    Returns:
        (category, check_type, confidence, category_code) or (None, None, 0.0, None) if no match.
    """
    if not text:
        return None, None, 0.0, None
    for rule in KEYWORD_RULES:
        if rule.pattern.search(text):
            return rule.category, rule.check_type, rule.confidence, rule.category_code
    return None, None, 0.0, None


def classify_comment(
    comment: dict[str, Any],
) -> tuple[str | None, str | None, float, str | None]:
    """Classify a single comment using sheet rule first, then keywords.

    Args:
        comment: crs_comment dict with 'detail_sheet', 'comment', 'group_comment'.

    Returns:
        (category, check_type, confidence, category_code) or (None, None, 0.0, None) if unmatched.
    """
    # Amendment #3: sheet rule has priority (0.95 confidence vs 0.85 for keywords)
    cat, chk, conf, cat_code = _classify_by_sheet(comment.get("detail_sheet"))
    if cat:
        return cat, chk, conf, cat_code

    text = comment.get("comment") or comment.get("group_comment") or ""
    return classify_by_keywords(text)


# ---------------------------------------------------------------------------
# Prefect task
# ---------------------------------------------------------------------------

@task(name="tier2-keyword-classifier", cache_policy=NO_CACHE)
def run_tier2(
    comments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Classify comments using sheet names and keyword regex rules (Tier 2).

    No DB access. No LLM. Pure deterministic classification.

    Uses group-by-apply: comments with the same generalised error pattern
    (differing only in specific tag names / doc numbers / counts) are grouped
    together. Classification runs ONCE per unique template and is broadcast
    to all rows in the group — reducing work from O(N) to O(M) where M << N.

    The first (representative) row in each group determines the classification.
    Sheet-rule classification uses the representative's detail_sheet; keyword
    classification uses the generalised text key (all rows in a group share
    the same underlying error pattern).

    Args:
        comments: Batch of unclassified comment dicts (passed from Tier 1).

    Returns:
        (unmatched, classified) — unmatched go to Tier 3 LLM.
    """
    logger = get_run_logger()

    # Group by generalised error pattern — M unique keys for N input rows
    groups = group_by_generalized(comments)

    group_results: dict[str, dict[str, Any]] = {}
    unmatched_keys: set[str] = set()
    sheet_matched = 0
    keyword_matched = 0

    for key, rows in groups.items():
        # Use the first row as the representative for rule evaluation
        representative = rows[0]

        # Sheet rule first (Amendment #3 — higher confidence than keyword regex)
        cat, chk, conf, cat_code = _classify_by_sheet(representative.get("detail_sheet"))
        if cat:
            sheet_matched += 1
        else:
            text = representative.get("comment") or representative.get("group_comment") or ""
            cat, chk, conf, cat_code = classify_by_keywords(text)
            if cat:
                keyword_matched += 1

        if cat:
            group_results[key] = {
                "llm_category":            cat,
                "llm_category_confidence": conf,
                "check_type":              chk,
                "classification_tier":     2,
                # IN_REVIEW: valid status in crs_comment_status_check constraint
                "status":                  "IN_REVIEW",
                "category_code":           cat_code,
                "category_confidence":     conf,
            }
        else:
            unmatched_keys.add(key)

    # Broadcast results to all rows in matched groups
    matched_groups = {k: v for k, v in groups.items() if k not in unmatched_keys}
    classified = broadcast_result(matched_groups, group_results)
    unmatched = [row for k in unmatched_keys for row in groups[k]]

    logger.info(
        "Tier 2: %d rows → %d unique templates; %d classified (sheet=%d, keyword=%d), "
        "%d unmatched → Tier 3.",
        len(comments), len(groups), len(classified), sheet_matched, keyword_matched,
        len(unmatched),
    )
    return unmatched, classified
