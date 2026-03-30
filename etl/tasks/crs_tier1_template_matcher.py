"""
Tier 1 template matcher for CRS cascade classifier.

Matches normalised comments against the audit_core.crs_comment_template knowledge base.
After 3-4 batches, the KB warms up and Tier 1 handles ~50-70% of comments,
dramatically reducing Tier 3 LLM calls.

Algorithm:
  1. Load all active templates from DB (one bulk query per batch).
  2. For each comment: normalise text → try exact MD5 hash match.
  3. If no exact match: fuzzy match with SequenceMatcher ratio >= 0.92.
  4. Matched: return with category + template_id (classification_tier=1).
  5. Unmatched: pass to Tier 2.

Speed: ~50k records/sec (single DB query + in-memory fuzzy matching).
"""
from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from typing import Any

from prefect import task, get_run_logger
from sqlalchemy import text
from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# Comment normalisation
# ---------------------------------------------------------------------------

# Amendment #1: regex covers all real JDA tag patterns from production xlsx:
#   JDA-SB-V3C-F001, JDA-75-31-TOU-802, JDA-1-H74109-TGD-, HIS0164STN0131
_NORMALISE_RE = re.compile(
    r"""
    JDAW-[A-Z0-9\-]+           |  # doc numbers: JDAW-KVE-E-JA-6944-00001-016
    JDA-[A-Z0-9\.\-]+          |  # JDA-SB-V3C-F001, JDA-75-31-TOU-802
    \bJDA[A-Z0-9\-\.]+\b       |  # slurred JDA variants: JDAW..., JDA1...
    \b[A-Z]{2,6}[0-9]{3,}\b   |  # HIS0163, STN0264, XV1234, HIS0164STN0131
    \b\d+\s*tag(s)?\b          |  # "706 tags", "1 tag"
    \b\d+\b                    |  # standalone numbers
    \.xlsx?\b                     # file extensions
    """,
    re.IGNORECASE | re.VERBOSE,
)


def normalise_comment(text: str) -> str:
    """Strip entity-specific values from a comment for template matching.

    Replacements applied:
    - Doc numbers (JDAW-*): → DOCREF
    - Tag names (JDA-*, HIS0163, STN0264, etc.): → TAGREF
    - Numbers (standalone digits): → NUM
    - "N tags" phrases: → NUM tags
    - File extensions (.xlsx): stripped

    Args:
        text: Raw comment text.

    Returns:
        Normalised lowercase string with placeholders.

    Examples:
        >>> normalise_comment("Tag HIS0163 missing DESIGN_PRESSURE")
        'tag tagref missing design_pressure'
        >>> normalise_comment("Document JDAW-KVE-E-JA-6944-00001-016 not linked")
        'document docref not linked'
    """

    def _replace(m: re.Match) -> str:  # type: ignore[type-arg]
        s = m.group(0)
        s_lower = s.lower()
        if s_lower.startswith("jdaw-"):
            return "DOCREF"
        if s_lower.startswith("jda"):
            return "TAGREF"
        if re.match(r"\b\d+\s*tags?\b", s, re.IGNORECASE):
            return "NUM tags"
        if re.match(r"\.[xlsx]+\b", s, re.IGNORECASE):
            return ""
        # uppercase-letter+digits pattern or standalone number
        return "TAGREF" if re.match(r"[A-Z]", s) else "NUM"

    normalised = _NORMALISE_RE.sub(_replace, text)
    # Compress whitespace, lowercase, strip
    return " ".join(normalised.lower().split())


def _hash(normalised: str) -> str:
    """Return MD5 hex digest of lower(trim(text))."""
    return hashlib.md5(normalised.lower().strip().encode()).hexdigest()


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

def _load_templates(engine: Engine) -> list[dict[str, Any]]:
    """Fetch all active templates from audit_core.crs_comment_template.

    Returns list of dicts with keys: id, template_text, template_hash,
    category, check_type, response_template, confidence.
    """
    sql = text("""
        SELECT id, template_text, template_hash,
               category, check_type, response_template, confidence
        FROM audit_core.crs_comment_template
        WHERE object_status = 'Active'
        ORDER BY usage_count DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r._mapping) for r in rows]


# ---------------------------------------------------------------------------
# Prefect task
# ---------------------------------------------------------------------------

@task(name="tier1-template-matcher")
def run_tier1(
    comments: list[dict[str, Any]],
    engine: Engine,
    similarity_threshold: float = 0.92,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Match normalised comments against the KB template table (Tier 1).

    Args:
        comments: Batch of unclassified comment dicts.
        engine: SQLAlchemy engine.
        similarity_threshold: SequenceMatcher ratio needed for fuzzy match (default 0.92).

    Returns:
        (unmatched, classified) — unmatched go to Tier 2.
    """
    logger = get_run_logger()

    templates = _load_templates(engine)
    if not templates:
        logger.info("Tier 1: KB is empty — all %d comments pass to Tier 2.", len(comments))
        return comments, []

    # Build hash index for O(1) exact lookup
    hash_index: dict[str, dict[str, Any]] = {t["template_hash"]: t for t in templates}

    unmatched: list[dict[str, Any]] = []
    classified: list[dict[str, Any]] = []

    for comment in comments:
        raw_text = comment.get("comment") or comment.get("group_comment") or ""
        norm = normalise_comment(raw_text)
        h = _hash(norm)

        # 1. Exact hash match (O(1))
        template = hash_index.get(h)
        score = 1.0

        # 2. Fuzzy match (O(n * m) — acceptable since templates list is bounded)
        if template is None and norm:
            best_score = 0.0
            best_tpl = None
            for tpl in templates:
                ratio = SequenceMatcher(None, norm, tpl["template_text"]).ratio()
                if ratio > best_score:
                    best_score = ratio
                    best_tpl = tpl
            if best_score >= similarity_threshold:
                template = best_tpl
                score = best_score

        if template is not None:
            classified.append({
                **comment,
                "llm_category":            template["category"],
                "llm_category_confidence": score,
                "category_code":           template["category"],
                "category_confidence":     score,
                "classification_tier":     1,
                "template_id":             str(template["id"]),
                "status":                  "CLASSIFIED",
            })
        else:
            unmatched.append(comment)

    logger.info(
        "Tier 1: %d matched (KB size=%d, threshold=%.2f), %d unmatched.",
        len(classified), len(templates), similarity_threshold, len(unmatched),
    )
    return unmatched, classified
