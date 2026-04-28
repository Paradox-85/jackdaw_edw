"""
Tier 3 LLM classifier for CRS cascade classifier.

Handles the ~5-10% of comments that couldn't be classified by Tiers 0-2.
Uses Qwen3.5-27B via llamacpp server (local LXC) in batch mode (32 items per call).
Thinking mode disabled server-side via --reasoning-budget 0 flag.

Process per comment:
  1. Extract parameters: tag_name, property_name, from_tag, to_tag, doc_number
  2. Look up matching validation query in audit_core.crs_validation_query
  3. Execute SQL verification query with extracted parameters
  4. Call LLM with comment + SQL result → get category + response
  5. Return with llm_category, confidence, classification_tier=3

Batch inference (32 items) reduces Ollama overhead by ~85% vs one-by-one calls.
LLM endpoint and model are read from config/config.yaml (llm.base_url, llm.model).
OLLAMA_BASE_URL / OLLAMA_MODEL env vars override config values (useful in CI/tests).

Only 100-200k comments reach this tier in steady state (5-10% of 2M total).

Status mapping (must satisfy crs_comment_status_check constraint):
  confidence >= 0.7 → IN_REVIEW   (was: CLASSIFIED   — not in constraint)
  confidence <  0.7 → DEFERRED    (was: PENDING_REVIEW — not in constraint)
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from etl.tasks.common import load_config, get_llm_config
# Regex patterns live in crs_text_generalizer (source of truth — breaks circular import).
# Dependency is one-way: crs_tier3 → crs_text_generalizer (never the reverse).
from etl.tasks.crs_text_generalizer import (
    broadcast_result,
    group_by_generalized,
    _TAG_RE,
    _DOC_RE,
    _PROPERTY_RE,
)

from prefect import task, get_run_logger
from prefect.cache_policies import NO_CACHE
from sqlalchemy import text
from sqlalchemy.engine import Engine

# LLM batch size — 32 items per Ollama call reduces per-item overhead ~85%
_LLM_BATCH_SIZE = 32

# Categories the LLM is allowed to return (validated on parse).
# CRS-C001..C050 = canonical categories; CRS-C051..C229 = granular sub-categories
# (assigned by migration_022_crs_template_harmonisation.sql — one code per row).
_VALID_CATEGORIES: frozenset[str] = frozenset(f"CRS-C{i:03d}" for i in range(1, 230))

# Fallback category dict — used when DB has no active templates (migration not applied,
# empty table, or DB unreachable). Ensures LLM always receives a non-empty category list.
# Source: audit_core.crs_comment_template WHERE object_status='Active', synced 2026-04-03.
# C051..C054 absent (no Active rows in DB). C133..C229 not yet Active — omitted.
# Re-sync: SELECT category_code, short_template_text FROM audit_core.crs_comment_template
#   WHERE object_status='Active' ORDER BY category_code;
_FALLBACK_CATEGORIES: dict[str, str] = {
    # --- CRS-C001..C050: canonical categories ---
    "CRS-C001": "missing required fields",
    "CRS-C002": "tag description missing",
    "CRS-C003": "description too long",
    "CRS-C004": "tag class not in RDL",
    "CRS-C005": "tag naming convention violated",
    "CRS-C006": "area code blank",
    "CRS-C007": "area code invalid",
    "CRS-C008": "process unit code missing",
    "CRS-C009": "process unit not in register",
    "CRS-C010": "parent tag missing for physical tag",
    "CRS-C011": "parent tag not in MTR",
    "CRS-C012": "pipe-to-pipe parent reference",
    "CRS-C013": "safety critical item blank or invalid",
    "CRS-C014": "safety critical reason missing",
    "CRS-C015": "production critical item blank",
    "CRS-C016": "duplicate tags",
    "CRS-C017": "property tag not in MTR",
    "CRS-C018": "UOM present when value is NA",
    "CRS-C019": "property value is zero",
    "CRS-C020": "property not in class scope",
    "CRS-C021": "tag has no properties",
    "CRS-C022": "mandatory property missing",
    "CRS-C023": "equipment class not in RDL",
    "CRS-C024": "equipment description blank",
    "CRS-C025": "manufacturer serial number blank",
    "CRS-C026": "model part name blank",
    "CRS-C027": "manufacturer company blank",
    "CRS-C028": "equipment tag not in MTR",
    "CRS-C029": "plant code invalid",
    "CRS-C030": "document missing or NYI/CAN status",
    "CRS-C031": "tag has no document reference",
    "CRS-C032": "document in mapping not in DocMaster",
    "CRS-C033": "tag in mapping not in MTR",
    "CRS-C034": "document area code missing",
    "CRS-C035": "document process unit missing",
    "CRS-C036": "PO code not in register",
    "CRS-C037": "PO date missing",
    "CRS-C038": "company name missing or invalid",
    "CRS-C039": "duplicate physical connections",
    "CRS-C040": "equipment has no document mapping",
    "CRS-C041": "EX class or IP grade missing",
    "CRS-C042": "MC package code missing",
    "CRS-C043": "heat tracing type missing",
    "CRS-C044": "insulation type missing",
    "CRS-C045": "from-tag or to-tag not in MTR",
    "CRS-C046": "tag linked to inactive document",
    "CRS-C047": "revision status inconsistent",
    "CRS-C048": "property UOM not in RDL",
    "CRS-C049": "tag status inconsistent with class",
    "CRS-C050": "circular parent hierarchy",
    # C051..C054: no Active rows in DB — intentionally omitted
    # --- CRS-C055..C132: granular sub-categories (migration_022) ---
    "CRS-C055": "Missing mandatory area data",
    "CRS-C056": "Tags mapped to incorrect area level",
    "CRS-C057": "Combined document file submitted",
    "CRS-C058": "Company name not in company register for PO",
    "CRS-C059": "Doc-area document not in DocMaster",
    "CRS-C060": "Doc-area reference missing area code",
    "CRS-C061": "Doc-equipment document not in DocMaster",
    "CRS-C062": "Doc-equipment equipment not in register",
    "CRS-C063": "Doc-equipment references model parts",
    "CRS-C064": "Doc numbers not matching DMS",
    "CRS-C065": "Doc-plant document not in DocMaster",
    "CRS-C066": "Doc-PO code not in PO register",
    "CRS-C067": "Doc-PO document not in DocMaster",
    "CRS-C068": "Doc-PU document not in DocMaster",
    "CRS-C069": "Doc-PU plant code not in register",
    "CRS-C070": "Doc-PU process unit not in register",
    "CRS-C071": "Doc-PU reference missing process unit code",
    "CRS-C072": "Doc revision mismatch with DMS",
    "CRS-C073": "Doc-site document not in DocMaster",
    "CRS-C074": "Doc-tag document not in DocMaster",
    "CRS-C075": "Doc-tag references tag not in MTR",
    "CRS-C076": "Doc title mismatch with DMS",
    "CRS-C077": "Document not in DMS or NYI",
    "CRS-C078": "Documents not in DMS or in NYI status",
    "CRS-C079": "Duplicate document records",
    "CRS-C080": "Equipment without document reference",
    "CRS-C081": "Layout drawing reference missing",
    "CRS-C082": "Loop diagram reference missing",
    "CRS-C083": "Outdated document template used",
    "CRS-C084": "PID schematic reference missing",
    "CRS-C085": "Site code format incorrect",
    "CRS-C086": "Tags without document references",
    "CRS-C087": "Void PO code in doc-PO reference",
    "CRS-C088": "Void tags have doc references",
    "CRS-C089": "Wrong CIS submission template used",
    "CRS-C090": "Wrong CSV template for doc-PU register",
    "CRS-C091": "Equipment class blank",
    "CRS-C092": "Equipment class not in ISM",
    "CRS-C093": "Equipment class vs description mismatch",
    "CRS-C094": "Equipment description duplicated",
    "CRS-C095": "Equipment description ends with dash",
    "CRS-C096": "Equipment description missing",
    "CRS-C097": "Equipment description spelling error",
    "CRS-C098": "Equipment description starts with dash",
    "CRS-C099": "Equipment description too short",
    "CRS-C100": "Equipment has no document references",
    "CRS-C101": "Equipment is own parent tag",
    "CRS-C102": "Equipment not matched with doc reference",
    "CRS-C104": "Equipment parent tag derivable from description",
    "CRS-C105": "Equipment plant code not in register",
    "CRS-C106": "Equipment tag not in MTR",
    "CRS-C107": "Equipment TNC non-compliance",
    "CRS-C108": "General equipment data missing",
    "CRS-C109": "Mandatory equipment fields blank",
    "CRS-C110": "Manufacturer serial number blank",
    "CRS-C111": "Manufacturer serial number is NA",
    "CRS-C112": "Manufacturing company not populated",
    "CRS-C113": "Model part name missing",
    "CRS-C114": "Tag register changes not in equipment register",
    "CRS-C115": "Duplicate equipment property entries",
    "CRS-C116": "Equipment class-property mapping mismatch",
    "CRS-C117": "Equipment has no properties",
    "CRS-C118": "Equipment in property register not in equip register",
    "CRS-C119": "Equipment property orphan record",
    "CRS-C120": "Equipment property register has tag numbers",
    "CRS-C121": "Equipment property value blank",
    "CRS-C122": "Equipment property value is zero",
    "CRS-C123": "Required ISM equipment properties not submitted",
    "CRS-C124": "UOM populated when property value is NA for equipment",
    "CRS-C125": "Wrong header in equipment property register",
    "CRS-C126": "Model part description not defined",
    "CRS-C127": "Model part not in model part register",
    "CRS-C128": "Model part number invalid characters",
    "CRS-C129": "Multiple process unit codes for same system",
    "CRS-C130": "Process unit description blank",
    "CRS-C131": "Process unit formatting inconsistent",
    "CRS-C132": "Process unit hierarchy inconsistent",
    # C133..C229: not yet Active in DB — omitted
}

# ---------------------------------------------------------------------------
# Parameter extraction
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Domain detection — seq-code routing (deterministic)
# Source of truth: eis_registers dict in the import flow.
# Seq-code = the 3-digit segment between the 5th and 6th dashes in the
# detail_sheet filename, e.g. "...00001-003-A36..." → "-003-" → "tag".
# Domain values MUST match check_type values in audit_core.crs_comment_template.
# ---------------------------------------------------------------------------

_SEQ_TO_DOMAIN: dict[str, str] = {
    "-001-": "area",                # EIS 203 — Area register
    "-002-": "process_unit",        # EIS 204 — ProcessUnit register
    "-003-": "tag",                 # EIS 205 — Tag Register (MTR)
    "-004-": "equipment",           # EIS 206 — Equipment Register
    "-005-": "model_part",          # EIS 209 — Model Part Register
    "-006-": "tag_connection",      # EIS 212 — Tag Physical Connections
    "-008-": "purchase_order",      # EIS 214 — Purchase Order Register
    "-009-": "tag_class_property",  # EIS 307 — Tag Class Properties (schema)
    "-010-": "tag_property",        # EIS 303 — Tag Property Values (EAV)
    "-011-": "equipment_property",  # EIS 301 — Equipment Property Values (EAV)
    "-016-": "document",            # EIS 412 — Doc→Tag
    "-017-": "document",            # EIS 411 — Doc→Area
    "-018-": "document",            # EIS 410 — Doc→ProcessUnit
    "-019-": "document",            # EIS 413 — Doc→Equipment
    "-020-": "document",            # EIS 414 — Doc→ModelPart
    "-022-": "document",            # EIS 420 — Doc→PurchaseOrder
    "-023-": "document",            # EIS 409 — Doc→PlantCode
    "-024-": "document",            # EIS 408 — Doc→Site
}

# All valid check_type values in audit_core.crs_comment_template.
# Must stay in sync with migration_022_crs_template_harmonisation.sql.
KNOWN_DOMAINS: list[str] = [
    "tag",
    "equipment",
    "tag_property",
    "equipment_property",
    "tag_connection",
    "tag_class_property",
    "document",
    "purchase_order",
    "process_unit",
    "area",
    "model_part",
]


def _detect_comment_domain(comment_text: str, detail_sheet: str = "") -> str:
    """Determine comment domain from detail_sheet filename seq-code only.

    Maps the seq-code segment (e.g. '-003-', '-016-') in the detail_sheet
    filename deterministically to a domain per the JDAW EIS register mapping.
    Returns '' if detail_sheet is absent or seq-code not recognised —
    _build_categories_line() with domain='' falls back to ALL templates
    (safe default: LLM sees full category list).
    """
    if detail_sheet:
        for seq, domain in _SEQ_TO_DOMAIN.items():
            if seq in detail_sheet:
                return domain
    return ""


def _extract_json_from_response(raw: str) -> dict[str, Any] | None:
    """Extract JSON from LLM response, handling Qwen3 thinking mode.

    Priority:
    1. Text after </think> tag (Qwen3 puts answer after thinking block)
    2. Text inside <output> tags
    3. Last JSON block in response (Qwen3 puts answer last)
    4. First JSON block anywhere (original fallback)
    """
    # Priority 1: after </think> tag
    after_think = re.split(r"</think>", raw, flags=re.IGNORECASE)
    candidates: list[str] = [after_think[-1]] if len(after_think) > 1 else []

    # Priority 2: inside <output> tags
    output_match = re.search(r"<output>(.*?)</output>", raw, re.DOTALL | re.IGNORECASE)
    if output_match:
        candidates.insert(0, output_match.group(1))

    # Priority 3 + 4: scan candidates then full raw; take last match in each
    candidates.append(raw)

    for text in candidates:
        # Try non-nested first (faster), then nested/greedy
        all_matches = list(re.finditer(r"\{[^{}]*\}", text, re.DOTALL))
        if not all_matches:
            all_matches = list(re.finditer(r"\{.*\}", text, re.DOTALL))
        for m in reversed(all_matches):
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                continue
    return None


def extract_parameters(comment_text: str) -> dict[str, str | None]:
    """Extract structured parameters from free-text CRS comment.

    Args:
        comment_text: Raw comment or group_comment text.

    Returns:
        Dict with keys: tag_name, property_name, doc_number, from_tag, to_tag.
        All values are str or None.
    """
    tags = _TAG_RE.findall(comment_text)
    docs = _DOC_RE.findall(comment_text)
    props = _PROPERTY_RE.findall(comment_text)

    return {
        "tag_name":      tags[0] if tags else None,
        "property_name": props[0] if props else None,
        "doc_number":    docs[0] if docs else None,
        "from_tag":      tags[0] if len(tags) >= 1 else None,
        "to_tag":        tags[1] if len(tags) >= 2 else None,
    }


# ---------------------------------------------------------------------------
# Validation query selection + execution
# ---------------------------------------------------------------------------

def _load_validation_queries(engine: Engine) -> list[dict[str, Any]]:
    """Load active validation queries from crs_validation_query registry."""
    sql = text("""
        SELECT query_code, category,
               sql_query, has_parameters, parameter_names
        FROM audit_core.crs_validation_query
        WHERE is_active = true AND object_status = 'Active'
        ORDER BY query_code
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r._mapping) for r in rows]


def _load_crs_templates(engine: Engine) -> list[dict[str, Any]]:
    """Load active CRS comment templates for category hint building."""
    sql = text("""
        SELECT category_code AS category, check_type, short_template_text
        FROM audit_core.crs_comment_template
        WHERE object_status = 'Active'
        ORDER BY category_code
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r._mapping) for r in rows]


def _build_categories_line(
    templates: list[dict[str, Any]],
    domain: str | None = None,
    max_chars: int = 10000,
) -> str:
    """Build compact category hints string for LLM prompt injection.

    Filters templates by check_type substring match against domain.
    Falls back to all templates if filtered list is empty or domain is None.

    Format per entry: "CRS-C001=tag not in register"
    """
    if not templates:
        return ""

    filtered = templates
    if domain:
        filtered = [
            t for t in templates
            if t.get("check_type") and domain.lower() in t["check_type"].lower()
        ]
        if not filtered:
            filtered = templates  # fallback to all

    parts: list[str] = []
    current_len = 0
    for t in filtered:
        cat = t.get("category") or "?"
        short = t.get("short_template_text")
        entry = f"{cat}={short[:40]}" if short else f"{cat}={t.get('check_type') or ''}"
        separator_len = 2 if parts else 0  # ", " between entries
        if current_len + separator_len + len(entry) > max_chars:
            break
        parts.append(entry)
        current_len += separator_len + len(entry)

    return ", ".join(parts)


def _select_query(
    params: dict[str, str | None],
    queries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Pick the most appropriate validation query given extracted params.

    Priority:
    1. If from_tag + to_tag → TAG_FROM_TO_LINK
    2. If doc_number → TAG_HAS_DOCUMENT
    3. If property_name → TAG_HAS_PROPERTY
    4. If tag_name → TAG_EXISTS
    5. Fallback → TAGS_WITHOUT_PROPERTIES (no params needed)
    """
    query_map = {q["query_code"]: q for q in queries}

    if params.get("from_tag") and params.get("to_tag"):
        return query_map.get("TAG_FROM_TO_LINK")
    if params.get("doc_number") and params.get("tag_name"):
        return query_map.get("TAG_HAS_DOCUMENT")
    if params.get("property_name") and params.get("tag_name"):
        return query_map.get("TAG_HAS_PROPERTY")
    if params.get("tag_name"):
        return query_map.get("TAG_EXISTS")
    return query_map.get("TAGS_WITHOUT_PROPERTIES")


def _run_verification(
    query: dict[str, Any],
    params: dict[str, str | None],
    engine: Engine,
) -> list[dict[str, Any]]:
    """Execute the validation SQL with extracted parameters.

    Returns:
        List of result row dicts (empty list if no rows or query fails).
    """
    try:
        sql_params: dict[str, str] = {}
        for p_name in (query.get("parameter_names") or []):
            val = params.get(p_name)
            sql_params[p_name] = val if val else ""

        with engine.connect() as conn:
            rows = conn.execute(text(query["sql_query"]), sql_params).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception as e:  # noqa: BLE001
        return [{"error": str(e)}]


# ---------------------------------------------------------------------------
# LLM inference (Qwen3 via Ollama)
# ---------------------------------------------------------------------------


def _first_nonempty(*values: str | None) -> str:
    """Return first non-empty, non-None value, stripping whitespace.

    Empty string "" is treated as empty (falsy in Python but valid DB value).
    This fixes the bug where `or` chains fail silently on empty strings.

    Args:
        *values: Values to check in order.

    Returns:
        First non-empty value stripped of whitespace, or "" if all empty/None.
    """
    for v in values:
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _build_prompt(
    comment: dict[str, Any],
    params: dict[str, str | None],
    sql_result: list[dict[str, Any]],
    categories_line: str,
) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) tuple for ChatOpenAI messages list."""
    import re as _re  # local — avoids shadowing module-level re

    text_val = _first_nonempty(
        comment.get("comment"),
        comment.get("group_comment"),
    )
    sheet = comment.get("detail_sheet") or "unknown"
    result_str = json.dumps(sql_result[:3], default=str)

    # Dynamically derive min/max CRS-C### from the categories_line passed in.
    # Falls back to "see list below" if parsing fails (empty line, no matches).
    _cat_nums = [int(m) for m in _re.findall(r"CRS-C(\d+)", categories_line)]
    if _cat_nums:
        _cat_range = f"CRS-C{min(_cat_nums):03d} through CRS-C{max(_cat_nums):03d}"
    else:
        _cat_range = "see list below"

    system_msg = (
        "You are an engineering data classification system. "
        "Output ONLY a single JSON object. "
        "No explanation. No markdown. "
        "Input rule (CRITICAL): The comment field is always evaluated AS A WHOLE. "
        "Never extract a fragment or sub-sentence for classification. "
        "If the comment contains multiple sentences or issues — that is the input. "
        "Evaluate it entirely as one unit. "
        "Classification rules: "
        "If the comment indicates a field is empty, blank, missing, not defined, "
        "null, unset, or not populated — the value is ABSENT. "
        "Match to a category whose description covers absent/missing values. "
        "Example: 'Area code is blank' → category for missing area code. "
        "If the comment indicates a field contains 'NA', 'N/A', 'n/a', "
        "'Not Applicable', 'none', or a similar placeholder — the value IS present "
        "but is a placeholder that fails validation. "
        "Match to a category whose description covers invalid or non-matching values. "
        "Example: 'Area code is NA' → category for invalid/non-matching area code. "
        "Apply this distinction to ALL field types, not just specific ones. "
        "Domain glossary (mandatory context — use this to interpret abbreviations): "
        "TNC = Tag Naming Convention: official project standard for naming tags and instruments. "
        "ISM = AVEVA ISM (Information Standards Management): software tool used to create and "
        "manage project RDL (Reference Data Library) and tag class definitions. "
        "EIS = Engineering Information Specification: governing project document defining data "
        "requirements, file naming rules, Excel templates, and containing RDL as an appendix. "
        "MTR = Master Tag Register: master register of all tags. "
        "RDL = Reference Data Library: catalogue of approved tag classes, UOMs, and codes. "
        "DMS = Document Management System (also called EDMS). "
        "CIS = Commissioning Information Submission: data package submitted per revision. "
        "PBS = Plant Breakdown Structure: hierarchy of plant areas and process units. "
        "PDMS = Plant Design Management System:3D CAD tool for piping and structural design. "
        "PEFS = Process Engineering Flow Scheme (also called P&ID or PID): piping and "
        "instrumentation diagram. "
        "AFC = Approved for Construction: document revision status. "
        "NYI = Not Yet Issued: document status indicating document exists in DMS but not yet issued. "
        "1ooN = One-out-of-N voting logic notation used in safety/instrumented systems "
        "(e.g. 1oo2 = one-out-of-two). This notation appears in tag descriptions — "
        "a comment asking 'what is 1oo2?' is a QUESTION about notation, not a data error. "
        "CP = Control Panel (appears in tag names). "
        "SP = Speciality Piping (a TNC category code). "
        "NRV = Non-Return Valve. "
        "SECE = Safety Critical Element. "
        "EPC = Engineering, Procurement and Construction (contractor type). "
        "Interpretation rules for abbreviations: "
        "(a) If a comment mentions TNC, it is asking about tag naming convention compliance. "
        "A TNC question without an explicit data error (missing/wrong field value) is "
        "ADVISORY — classify as OTHER with confidence <= 0.30. "
        "(b) If a comment contains 1ooN notation (1oo2, 1oo4, 1oo7, etc.) as a question, "
        "it is asking about instrument voting logic — classify as OTHER with confidence <= 0.30. "
        "(c) If a comment combines a known data error WITH a TNC/1ooN question, "
        "the combined comment is MULTI-TOPIC — classify as OTHER with confidence <= 0.30. "
        "Confidence rules (CRITICAL — follow exactly): "
        "Set confidence >= 0.85 ONLY when the ENTIRE comment clearly and "
        "unambiguously maps to a single category description. "
        "Set confidence between 0.50 and 0.69 when the comment is related to a "
        "category but the match is partial, indirect, or requires interpretation. "
        "Set confidence <= 0.30 and category 'OTHER' in ALL of these cases: "
        "(a) the comment is a recommendation or suggestion rather than a data error; "
        "(b) the comment is informational or advisory; "
        "(c) the comment contains two or more unrelated issues — even if one part "
        "matches a category, the whole does not; "
        "(d) no single category covers the full meaning of the entire comment; "
        "(e) you are uncertain or guessing. "
        "Never force a category match when none fits — a confident wrong answer is "
        "worse than an honest low-confidence OTHER. "
        "CRITICAL OVERRIDE: If your confidence value is 0.30 or lower, you MUST set "
        "category to 'OTHER'. Outputting any specific CRS-Cxxx code with confidence "
        "<= 0.30 is a logical contradiction and is strictly forbidden. "
        'Respond ONLY with: {"category":"CRS-C???","confidence":0.0,"response":"one sentence max"}'
    )
    user_msg = (
        f"CLASSIFY THIS COMMENT:\n"
        f"Sheet: {sheet}\n"
        f"Comment: {text_val}\n"
        f"DB check: {result_str}\n\n"
        f"Valid categories: {_cat_range}\n"
        f"({categories_line})\n\n"
        f'OUTPUT (JSON only): {{"category":"CRS-C???","confidence":0.0,"response":"one sentence max"}}'
    )
    return system_msg, user_msg


def _call_llm_batch(
    prompts: list[tuple[str, str] | str],
    model: str,
    base_url: str,
    api_key: str = "none",
    temperature: float = 0.1,
    max_tokens: int = 512,
    logger: Any = None,
    timeout: float = 30.0,
) -> list[dict[str, Any]]:
    """Call Ollama LLM for a batch of prompts.

    Uses langchain_openai.ChatOpenAI pointed at local Ollama endpoint.
    Logs every error explicitly so connection issues are visible in Prefect UI.

    Args:
        prompts: List of prompt strings (max 32 recommended).
        model: Ollama model name (e.g. 'qwen35-27b').
        base_url: Ollama OpenAI-compatible endpoint URL.
        api_key: API key for the endpoint (dummy value for local Ollama).
        temperature: Sampling temperature (lower = more deterministic).
        max_tokens: Maximum tokens per response.
        logger: Prefect run logger for explicit error reporting.

    Returns:
        List of parsed result dicts with keys: category, confidence, response.
    """
    try:
        from langchain_openai import ChatOpenAI  # type: ignore[import]
        from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import]
    except ImportError as e:
        msg = f"langchain_openai not installed: {e}"
        if logger:
            logger.error("Tier 3 LLM unavailable — %s", msg)
        return [{"category": "OTHER", "confidence": 0.5, "response": msg}] * len(prompts)

    llm = ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        http_client=httpx.Client(timeout=timeout),
        # thinking disabled server-side via --reasoning-budget 0 on llamacpp-qwen27b
    )

    results: list[dict[str, Any]] = []

    for i, prompt in enumerate(prompts):
        try:
            if isinstance(prompt, tuple):
                system_content, user_content = prompt
                messages = [
                    SystemMessage(content=system_content),
                    HumanMessage(content=user_content),
                ]
            else:
                messages = [HumanMessage(content=prompt)]
            msg = llm.invoke(messages)
            raw = msg.content.strip()
            if logger:
                logger.debug(
                    "Tier 3 LLM raw response (prompt #%d, len=%d): %r",
                    i, len(raw), raw[:500] if len(raw) > 500 else raw,
                )
            # Extract JSON block if wrapped in markdown
            parsed = _extract_json_from_response(raw)
            if parsed is not None:
                cat = parsed.get("category", "OTHER")
                # Guard: LLM returning a specific category with confidence <= 0.30 is a
                # logical contradiction (model admits it cannot classify but picks a code).
                # Force OTHER so status mapping correctly routes to NEEDS_NEW_CATEGORY.
                _conf_raw = float(parsed.get("confidence", 0.7))
                if _conf_raw <= 0.30 and cat != "OTHER":
                    cat = "OTHER"
                # UNCLASSIFIED is internal error sentinel — LLM returning it maps to OTHER
                if cat not in _VALID_CATEGORIES:
                    cat = "OTHER"
                resp = (parsed.get("response") or "").strip()
                if not resp:
                    conf_val = parsed.get("confidence", 0.7)
                    resp = f"Auto-classified as {cat} (confidence: {float(conf_val):.0%})"
                results.append({
                    "category":   cat,
                    "confidence": float(parsed.get("confidence", 0.7)),
                    "response":   resp,
                })
            else:
                if logger:
                    logger.warning(
                        "Tier 3: LLM returned non-JSON for prompt #%d "
                        "(raw len=%d, first 500 chars): %s",
                        i, len(raw), raw[:500] if raw else "<EMPTY STRING>",
                    )
                results.append({"category": "OTHER", "confidence": 0.5, "response": raw[:200]})
        except Exception as e:  # noqa: BLE001
            err_type = type(e).__name__
            err_short = str(e)[:120]
            # Log EVERY connection/timeout error explicitly — previously silent
            if logger:
                logger.warning(
                    "Tier 3: LLM call failed for prompt #%d — %s: %s",
                    i, err_type, e,
                )
            results.append({
                "category":   "UNCLASSIFIED",
                "confidence": 0.0,
                "response":   f"[LLM_ERROR:{err_type}] {err_short}",
            })
    return results


def _call_llm_single_debug(
    prompt: tuple[str, str],
    model: str,
    base_url: str,
    api_key: str = "none",
    temperature: float = 0.1,
    max_tokens: int = 512,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Single-prompt LLM call returning raw response + token usage for debugging.

    Args:
        prompt: (system_content, user_content) tuple.
        model: Ollama model name.
        base_url: Ollama OpenAI-compatible endpoint URL.
        api_key: API key (dummy value for local Ollama).
        temperature: Sampling temperature.
        max_tokens: Maximum tokens per response.
        timeout: Request timeout in seconds.

    Returns:
        Dict with keys:
            category, confidence, response — parsed result (same as _call_llm_batch)
            raw_response                  — full raw string from LLM
            prompt_tokens, completion_tokens, total_tokens — from response_metadata
            error                         — error string if call failed, else None
    """
    from langchain_openai import ChatOpenAI  # type: ignore[import]
    from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import]

    llm = ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        http_client=httpx.Client(timeout=timeout),
    )
    system_content, user_content = prompt
    messages = [SystemMessage(content=system_content), HumanMessage(content=user_content)]

    base_result: dict[str, Any] = {
        "category":          "UNCLASSIFIED",
        "confidence":        0.0,
        "response":          "",
        "raw_response":      "",
        "prompt_tokens":     0,
        "completion_tokens": 0,
        "total_tokens":      0,
        "error":             None,
    }
    try:
        msg = llm.invoke(messages)
        raw = msg.content.strip()
        base_result["raw_response"] = raw

        # Token usage — LangChain stores in response_metadata under token_usage key
        usage = getattr(msg, "response_metadata", {}).get("token_usage") or {}
        base_result["prompt_tokens"]     = usage.get("prompt_tokens", 0)
        base_result["completion_tokens"] = usage.get("completion_tokens", 0)
        base_result["total_tokens"]      = usage.get("total_tokens", 0)

        parsed = _extract_json_from_response(raw)
        if parsed:
            cat = parsed.get("category", "OTHER")
            # Guard: LLM returning a specific category with confidence <=0.30 is a
            # logical contradiction (model admits it cannot classify but picks a code).
            # Force OTHER so status mapping correctly routes to NEEDS_NEW_CATEGORY.
            _conf_raw = float(parsed.get("confidence",0.7))
            if _conf_raw <= 0.30 and cat != "OTHER":
                cat = "OTHER"
            if cat not in _VALID_CATEGORIES and cat != "UNCLASSIFIED":
                cat = "OTHER"
            resp = (parsed.get("response") or "").strip()
            if not resp:
                resp = f"Auto-classified as {cat}"
            base_result.update({
                "category":   cat,
                "confidence": float(parsed.get("confidence", 0.7)),
                "response":   resp,
            })
        else:
            base_result.update({
                "category":   "OTHER",
                "confidence": 0.5,
                "response":   raw[:200],
            })
    except Exception as e:  # noqa: BLE001
        base_result["error"] = f"{type(e).__name__}: {e}"

    return base_result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_llm_url(llm_cfg: dict) -> str:
    """Resolve LLM endpoint URL with priority:
    OLLAMA_BASE_URL (CI override) > OLLAMA_URL (docker-compose) > config.yaml llm.base_url.
    OLLAMA_URL is normalised: /v1 suffix added if missing.
    """
    if os.environ.get("OLLAMA_BASE_URL"):
        return os.environ["OLLAMA_BASE_URL"]
    if os.environ.get("OLLAMA_URL"):
        url = os.environ["OLLAMA_URL"].rstrip("/")
        return url if url.endswith("/v1") else url + "/v1"
    return llm_cfg.get("base_url", "")


# ---------------------------------------------------------------------------
# Prefect task
# ---------------------------------------------------------------------------

@task(name="tier3-llm-classifier", retries=2, cache_policy=NO_CACHE)
def run_tier3_llm(
    comments: list[dict[str, Any]],
    engine: Engine,
    two_pass: bool | None = None,   # None → read from env TIER3_TWO_PASS; default False
) -> list[dict[str, Any]]:
    """LLM-based classification for complex/unclear comments (Tier 3).

    Only 5-10% of original comments should reach this tier in steady state.
    Results are fed back into the template KB via update_template_db().

    Uses group-by-apply: comments with the same generalised error pattern are
    grouped together. LLM is called ONCE per unique template (representative
    row), then results are broadcast to all rows in the group. Reduces LLM
    calls from O(N) to O(M) where M << N in production.

    Two-pass strategy per unique template:
      Pass 1: narrow prompt filtered by detected comment domain (tag / document /
              property / safety / revision / other). Reduces token usage ~60%.
      Pass 2: if Pass 1 returns OTHER with confidence < 0.5, retry once with
              the full category list. Ensures no comment is left with stale hints.
              Disable via env var TIER3_TWO_PASS=false.

    Status mapping (must satisfy crs_comment_status_check constraint):
      cat == 'OTHER' and confidence <= 0.30 → NEEDS_NEW_CATEGORY
      confidence >= 0.7                     → IN_REVIEW
      confidence <  0.7                     → DEFERRED

    Args:
        comments: Batch of unclassified comment dicts (passed from Tier 2).
        engine: SQLAlchemy engine for validation SQL execution.

    Returns:
        List of classified comment dicts (same length as input).
    """
    logger = get_run_logger()

    # config.yaml is the source of truth; env vars override for CI/testing only
    llm_cfg = get_llm_config(load_config())
    # load_config() already overlays config/.env — llm_cfg["api_key"] has the real key.
    # OLLAMA_* env vars still work as highest-priority override for CI/testing.
    ollama_base_url = _resolve_llm_url(llm_cfg)
    ollama_model    = os.environ.get("OLLAMA_MODEL")    or llm_cfg["model"]
    ollama_api_key  = os.environ.get("OLLAMA_API_KEY")  or llm_cfg.get("api_key", "none")
    if two_pass is not None:
        two_pass_enabled = two_pass
    else:
        # env var default is now "false" — single-pass with full category list
        two_pass_enabled = os.environ.get("TIER3_TWO_PASS", "false").lower() == "true"

    # Log endpoint so it's always visible in Prefect UI — helps diagnose connectivity fast
    logger.info("Tier 3: using Ollama endpoint=%s model=%s two_pass=%s",
                ollama_base_url, ollama_model, two_pass_enabled)
    _key_preview = ollama_api_key[:4] + "**" if len(ollama_api_key) > 4 else "**"
    logger.info("Tier 3: LLM auth key prefix=%s endpoint=%s", _key_preview, ollama_base_url)

    # Load validation queries and category templates once per task call
    validation_queries = _load_validation_queries(engine)
    if not validation_queries:
        logger.warning("Tier 3: No active validation queries found in crs_validation_query.")

    crs_templates = _load_crs_templates(engine)
    if not crs_templates:
        logger.warning(
            "Tier 3: No active templates in DB — using fallback category dict "
            "(%d entries). Run migration_021_crs_short_text_seed.sql to seed the KB.",
            len(_FALLBACK_CATEGORIES),
        )
        crs_templates = [
            {"category": cat, "check_type": None, "short_template_text": desc}
            for cat, desc in _FALLBACK_CATEGORIES.items()
        ]

    # Group by generalised pattern — classify once per unique template (M << N)
    groups = group_by_generalized(comments)

    # Prepare prompts and metadata for unique template representatives
    unique_keys: list[str] = []
    unique_prompts: list[tuple[str, str]] = []
    unique_params: list[dict[str, str | None]] = []
    unique_sql_results: list[list[dict[str, Any]]] = []
    unique_reps: list[dict[str, Any]] = []
    unique_domains: list[str] = []

    for key, rows in groups.items():
        # Prefer a row where `comment` differs from `group_comment` (specific error text).
        # Falls back to rows[0] if all rows share the same comment/group_comment value.
        rep = next(
            (r for r in rows
             if r.get("comment") and r.get("comment") != r.get("group_comment")),
            rows[0],
        )
        text_val = rep.get("comment") or rep.get("group_comment") or ""

        # Normalise: always use "comment" key for _build_prompt()
        # This ensures _build_prompt() finds text via comment.get("comment")
        rep = {**rep, "comment": text_val}

        params = extract_parameters(text_val)
        if rep.get("from_tag"):
            params["from_tag"] = rep["from_tag"]
        if rep.get("to_tag"):
            params["to_tag"] = rep["to_tag"]
        if rep.get("tag_name"):
            params["tag_name"] = rep["tag_name"]
        if rep.get("property_name"):
            params["property_name"] = rep["property_name"]
        if rep.get("document_number"):
            params["doc_number"] = rep["document_number"]

        vq = _select_query(params, validation_queries)
        sql_result: list[dict[str, Any]] = []
        if vq:
            sql_result = _run_verification(vq, params, engine)

        # Domain derived from detail_sheet filename seq-code (deterministic).
        # rep is the representative row for this comment group.
        domain = _detect_comment_domain(text_val, detail_sheet=rep.get("detail_sheet", ""))
        if two_pass_enabled:
            # Two-pass: Pass 1 uses domain-filtered narrow list
            categories_pass1 = _build_categories_line(crs_templates, domain=domain)
        else:
            # Single-pass (default): full category list from the start
            categories_pass1 = _build_categories_line(crs_templates, domain=None)

        unique_keys.append(key)
        unique_prompts.append(_build_prompt(rep, params, sql_result, categories_pass1))
        unique_domains.append(domain)
        unique_params.append(params)
        unique_sql_results.append(sql_result)
        unique_reps.append(rep)

    # Batch LLM calls over unique prompts (M calls instead of N)
    all_llm_outputs: list[dict[str, Any]] = []
    total_pass2_retried = 0

    for batch_start in range(0, len(unique_prompts), _LLM_BATCH_SIZE):
        batch_prompts = unique_prompts[batch_start : batch_start + _LLM_BATCH_SIZE]

        for _pi, (_pk, _pp, _dom) in enumerate(zip(
                unique_keys[batch_start : batch_start + _LLM_BATCH_SIZE],
                batch_prompts,
                unique_domains[batch_start : batch_start + _LLM_BATCH_SIZE])):
            _sys, _usr = _pp if isinstance(_pp, tuple) else ("", _pp)
            _cat_count = _usr.count("CRS-C")
            logger.info(
                "Tier 3 [#%d/%d] domain=%-10s categories_in_prompt=%d key=%r",
                batch_start + _pi + 1, len(unique_keys),
                _dom, _cat_count, _pk[:60],
            )
            logger.debug(
                "Tier 3 [#%d] FULL PROMPT\n--- SYSTEM ---\n%s\n--- USER ---\n%s\n--- END ---",
                batch_start + _pi + 1, _sys, _usr,
            )

        llm_outputs = _call_llm_batch(
            batch_prompts,
            ollama_model,
            ollama_base_url,
            api_key=ollama_api_key,
            temperature=llm_cfg.get("temperature", 0.1),
            max_tokens=int(llm_cfg.get("max_tokens", 512)),
            logger=logger,
        )

        # Pass 2: retry OTHER/low-confidence templates with full category list
        if two_pass_enabled:
            retry_local = [
                i for i, out in enumerate(llm_outputs)
                if out["category"] == "OTHER" and out["confidence"] < 0.5
            ]
            if retry_local:
                categories_full = _build_categories_line(crs_templates, domain=None)
                retry_prompts = [
                    _build_prompt(unique_reps[batch_start + i],
                                  unique_params[batch_start + i],
                                  unique_sql_results[batch_start + i],
                                  categories_full)
                    for i in retry_local
                ]
                retry_outputs = _call_llm_batch(
                    retry_prompts,
                    ollama_model,
                    ollama_base_url,
                    api_key=ollama_api_key,
                    temperature=llm_cfg.get("temperature", 0.1),
                    max_tokens=int(llm_cfg.get("max_tokens", 512)),
                    logger=logger,
                )
                for local_i, out in zip(retry_local, retry_outputs):
                    llm_outputs[local_i] = out
                total_pass2_retried += len(retry_local)
                logger.info(
                    "Tier 3: Pass 2 retried %d items with full category list.",
                    len(retry_local),
                )
        else:
            # Single-pass mode: no retry — full category list was used in Pass 1
            pass

        all_llm_outputs.extend(llm_outputs)

    # Build key → classification fields mapping for broadcast
    key_results: dict[str, dict[str, Any]] = {}
    for key, llm_out, params, domain in zip(
            unique_keys, all_llm_outputs, unique_params, unique_domains):
        confidence = llm_out.get("confidence", 0.7)
        cat = llm_out["category"]
        # UNCLASSIFIED (LLM connection error, confidence=0.0) → DEFERRED automatically
        if cat == "OTHER" and confidence <= 0.30:
            status = "NEEDS_NEW_CATEGORY"
        elif confidence >= 0.7:
            status = "IN_REVIEW"
        else:
            status = "DEFERRED"

        key_results[key] = {
            "llm_category":            cat,
            "llm_category_confidence": confidence,
            "llm_response":            llm_out.get("response", ""),
            "llm_model_used":          ollama_model,
            "classification_tier":     3,
            "status":                  status,
            "_extracted_params":       params,
            "category_code":           cat,
            "category_confidence":     confidence,
            "check_type":              domain,
        }

    # Broadcast: fan out classification result to all rows in each group
    results = broadcast_result(groups, key_results)

    in_review = sum(1 for r in results if r.get("status") == "IN_REVIEW")
    deferred = sum(1 for r in results if r.get("status") == "DEFERRED")
    # Count broadcast rows (N) — consistent with in_review/deferred which also use results
    llm_errors = sum(
        1 for r in results
        if (r.get("llm_response") or "").startswith("[LLM_ERROR:")
    )
    logger.info(
        "Tier 3: %d rows → %d unique templates | %d in_review, %d deferred, "
        "%d pass2_retried, %d llm_errors (model=%s).",
        len(results), len(unique_keys), in_review, deferred,
        total_pass2_retried, llm_errors, ollama_model,
    )
    return results
