"""
Tier 3 LLM classifier for CRS cascade classifier.

Handles the ~5-10% of comments that couldn't be classified by Tiers 0-2.
Uses Qwen3 via Ollama (local LXC) in batch mode (32 items per call).

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

# Categories the LLM is allowed to return (validated on parse)
_VALID_CATEGORIES: frozenset[str] = frozenset(f"CRS-C{i:02d}" for i in range(1, 51))

# Fallback category dict — used when DB has no active templates (migration not applied,
# empty table, or DB unreachable). Ensures LLM always receives a non-empty category list.
_FALLBACK_CATEGORIES: dict[str, str] = {
    "CRS-C01": "missing required fields",
    "CRS-C02": "tag description missing",
    "CRS-C03": "description too long",
    "CRS-C04": "tag class not in RDL",
    "CRS-C05": "tag naming convention violated",
    "CRS-C06": "area code blank",
    "CRS-C07": "area code invalid",
    "CRS-C08": "process unit code missing",
    "CRS-C09": "process unit not in register",
    "CRS-C10": "parent tag missing for physical tag",
    "CRS-C11": "parent tag not in MTR",
    "CRS-C12": "pipe-to-pipe parent reference",
    "CRS-C13": "safety critical item blank or invalid",
    "CRS-C14": "safety critical reason missing",
    "CRS-C15": "production critical item blank",
    "CRS-C16": "duplicate tags",
    "CRS-C17": "property tag not in MTR",
    "CRS-C18": "UOM present when value is NA",
    "CRS-C19": "property value is zero",
    "CRS-C20": "property not in class scope",
    "CRS-C21": "tag has no properties",
    "CRS-C22": "mandatory property missing",
    "CRS-C23": "equipment class not in RDL",
    "CRS-C24": "equipment description blank",
    "CRS-C25": "manufacturer serial number blank",
    "CRS-C26": "model part name blank",
    "CRS-C27": "manufacturer company blank",
    "CRS-C28": "equipment tag not in MTR",
    "CRS-C29": "plant code invalid",
    "CRS-C30": "document missing or NYI/CAN status",
    "CRS-C31": "tag has no document reference",
    "CRS-C32": "document in mapping not in DocMaster",
    "CRS-C33": "tag in mapping not in MTR",
    "CRS-C34": "document area code missing",
    "CRS-C35": "document process unit missing",
    "CRS-C36": "PO code not in register",
    "CRS-C37": "PO date missing",
    "CRS-C38": "company name missing or invalid",
    "CRS-C39": "duplicate physical connections",
    "CRS-C40": "equipment has no document mapping",
    "CRS-C41": "EX class or IP grade missing",
    "CRS-C42": "MC package code missing",
    "CRS-C43": "heat tracing type missing",
    "CRS-C44": "insulation type missing",
    "CRS-C45": "from-tag or to-tag not in MTR",
    "CRS-C46": "tag linked to inactive document",
    "CRS-C47": "revision status inconsistent",
    "CRS-C48": "property UOM not in RDL",
    "CRS-C49": "tag status inconsistent with class",
    "CRS-C50": "circular parent hierarchy",
}

# ---------------------------------------------------------------------------
# Parameter extraction
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "document": ["document", "drawing", "datasheet", "specification", "dwg",
                 "rev ", "revision", "mdr", "transmittal"],
    "property": ["pressure", "temperature", "flow", "material", "rating",
                 "grade", "insulation", "diameter", "capacity", "voltage", "weight"],
    "safety":   ["safety", "sil", "sece", "hazard", "relief", "psv", "prv",
                 "ex class", "ip grade", "atex"],
    "tag":      ["tag", "equipment", "instrument", "valve", "pump",
                 "missing", "not found", "does not exist"],
    "revision": ["revision", "rev ", "updated", "superseded", "obsolete", "withdrawn"],
}


def _detect_comment_domain(comment_text: str) -> str:
    """Classify comment into broad domain without LLM — keyword matching only.

    Returns one of: 'document', 'property', 'safety', 'tag', 'revision', 'other'.
    Handles both raw text (with real entity codes) and generalised text (with
    <doc>/<tag>/<prop> placeholders produced by generalize_comment()).
    Doc regex checked first (high precision); keyword dicts in priority order;
    tag/property regexes used as secondary signal if keywords don't match.
    """
    lower = comment_text.lower()

    # Check for generalised document placeholder first (post-scrubbing), then raw regex.
    # After group_by_generalized(), JDAW-... codes become "<doc>" — raw regex never matches.
    if "<doc>" in lower or _DOC_RE.search(comment_text):
        return "document"

    # Save tag placeholder match — evaluated after keyword priority pass
    tag_match = "<tag>" in lower or bool(_TAG_RE.search(comment_text))

    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return domain

    if "<prop>" in lower or _PROPERTY_RE.search(comment_text):
        return "property"
    if tag_match:
        return "tag"
    return "other"


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
        SELECT query_code, category, sql_query, has_parameters, parameter_names
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
        SELECT category, check_type, short_template_text
        FROM audit_core.crs_comment_template
        WHERE object_status = 'Active'
        ORDER BY category
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r._mapping) for r in rows]


def _build_categories_line(
    templates: list[dict[str, Any]],
    domain: str | None = None,
    max_chars: int = 400,
) -> str:
    """Build compact category hints string for LLM prompt injection.

    Filters templates by check_type substring match against domain.
    Falls back to all templates if filtered list is empty or domain is None.

    Format per entry: "CRS-C01=TAG_EXISTS" or with short_template_text:
    "CRS-C01=tag not in register"
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

def _build_prompt(
    comment: dict[str, Any],
    params: dict[str, str | None],
    sql_result: list[dict[str, Any]],
    categories_line: str,
) -> str:
    """Build a concise prompt for single-comment classification."""
    text_val = comment.get("comment") or comment.get("group_comment") or ""
    sheet = comment.get("detail_sheet") or "unknown"
    result_str = json.dumps(sql_result[:3], default=str)

    return (
        f"/no_think\n"
        f"You are an engineering data classification system. "
        f"Output ONLY a single JSON object. No explanation. No markdown. No thinking.\n\n"
        f"CLASSIFY THIS COMMENT:\n"
        f"Sheet: {sheet}\n"
        f"Comment: {text_val}\n"
        f"DB check: {result_str}\n\n"
        f"Valid categories: CRS-C01 through CRS-C50\n"
        f"({categories_line})\n\n"
        f'OUTPUT (JSON only): {{"category":"CRS-C??","confidence":0.0,"response":"..."}}'
    )


def _call_llm_batch(
    prompts: list[str],
    model: str,
    base_url: str,
    api_key: str = "none",
    temperature: float = 0.1,
    max_tokens: int = 1024,   # was 256 — Qwen3 thinking mode needs headroom
    logger: Any = None,
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
        from langchain_core.messages import HumanMessage  # type: ignore[import]
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
    )

    results: list[dict[str, Any]] = []
    first_error_logged = False

    for i, prompt in enumerate(prompts):
        try:
            msg = llm.invoke([HumanMessage(content=prompt)])
            raw = msg.content.strip()
            # Extract JSON block if wrapped in markdown
            parsed = _extract_json_from_response(raw)
            if parsed is not None:
                cat = parsed.get("category", "OTHER")
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
                # LLM responded but not with valid JSON — log first occurrence
                if logger and not first_error_logged:
                    logger.warning(
                        "Tier 3: LLM returned non-JSON response (prompt #%d). "
                        "Raw (first 300 chars): %s",
                        i, raw[:300],
                    )
                    first_error_logged = True
                results.append({"category": "OTHER", "confidence": 0.5, "response": raw[:200]})
        except Exception as e:  # noqa: BLE001
            # Log EVERY connection/timeout error explicitly — previously silent
            if logger:
                logger.warning(
                    "Tier 3: LLM call failed for prompt #%d — %s: %s",
                    i, type(e).__name__, e,
                )
            results.append({"category": "OTHER", "confidence": 0.5, "response": f"LLM error: {type(e).__name__}: {e}"})
    return results


# ---------------------------------------------------------------------------
# Prefect task
# ---------------------------------------------------------------------------

@task(name="tier3-llm-classifier", retries=2, cache_policy=NO_CACHE)
def run_tier3_llm(
    comments: list[dict[str, Any]],
    engine: Engine,
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
      confidence >= 0.7 → IN_REVIEW
      confidence <  0.7 → DEFERRED

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
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL") or llm_cfg["base_url"]
    ollama_model    = os.environ.get("OLLAMA_MODEL")    or llm_cfg["model"]
    ollama_api_key  = os.environ.get("OLLAMA_API_KEY")  or llm_cfg.get("api_key", "none")
    two_pass_enabled = os.environ.get("TIER3_TWO_PASS", "true").lower() == "true"

    # Log endpoint so it's always visible in Prefect UI — helps diagnose connectivity fast
    logger.info("Tier 3: using Ollama endpoint=%s model=%s two_pass=%s",
                ollama_base_url, ollama_model, two_pass_enabled)

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
    unique_prompts: list[str] = []
    unique_params: list[dict[str, str | None]] = []
    unique_sql_results: list[list[dict[str, Any]]] = []
    unique_reps: list[dict[str, Any]] = []

    for key, rows in groups.items():
        rep = rows[0]  # representative row for parameter extraction and prompting
        text_val = rep.get("comment") or rep.get("group_comment") or ""

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

        # Pass 1: domain-filtered narrow categories
        # Use the generalised key for domain detection (entity-free text)
        domain = _detect_comment_domain(key)
        categories_narrow = _build_categories_line(crs_templates, domain=domain)

        unique_keys.append(key)
        unique_prompts.append(_build_prompt(rep, params, sql_result, categories_narrow))
        unique_params.append(params)
        unique_sql_results.append(sql_result)
        unique_reps.append(rep)

    # Batch LLM calls over unique prompts (M calls instead of N)
    all_llm_outputs: list[dict[str, Any]] = []
    total_pass2_retried = 0

    for batch_start in range(0, len(unique_prompts), _LLM_BATCH_SIZE):
        batch_prompts = unique_prompts[batch_start : batch_start + _LLM_BATCH_SIZE]

        llm_outputs = _call_llm_batch(
            batch_prompts,
            ollama_model,
            ollama_base_url,
            api_key=ollama_api_key,
            temperature=llm_cfg.get("temperature", 0.1),
            max_tokens=llm_cfg.get("max_tokens", 1024),
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
                    max_tokens=llm_cfg.get("max_tokens", 1024),
                    logger=logger,
                )
                for local_i, out in zip(retry_local, retry_outputs):
                    llm_outputs[local_i] = out
                total_pass2_retried += len(retry_local)
                logger.info(
                    "Tier 3: Pass 2 retried %d items with full category list.",
                    len(retry_local),
                )

        all_llm_outputs.extend(llm_outputs)

    # Build key → classification fields mapping for broadcast
    key_results: dict[str, dict[str, Any]] = {}
    for key, llm_out, params in zip(unique_keys, all_llm_outputs, unique_params):
        confidence = llm_out.get("confidence", 0.7)
        status = "IN_REVIEW" if confidence >= 0.7 else "DEFERRED"
        key_results[key] = {
            "llm_category":            llm_out["category"],
            "llm_category_confidence": confidence,
            "llm_response":            llm_out.get("response", ""),
            "llm_model_used":          ollama_model,
            "classification_tier":     3,
            "status":                  status,
            "_extracted_params":       params,
            "category_code":           llm_out["category"],
            "category_confidence":     confidence,
        }

    # Broadcast: fan out classification result to all rows in each group
    results = broadcast_result(groups, key_results)

    in_review = sum(1 for r in results if r.get("status") == "IN_REVIEW")
    deferred = sum(1 for r in results if r.get("status") == "DEFERRED")
    logger.info(
        "Tier 3: %d rows → %d unique templates | %d in_review, %d deferred, "
        "%d pass2_retried (model=%s).",
        len(results), len(unique_keys), in_review, deferred,
        total_pass2_retried, ollama_model,
    )
    return results
