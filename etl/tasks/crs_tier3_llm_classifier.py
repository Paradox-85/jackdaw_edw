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
OLLAMA_BASE_URL environment variable must be set to the LXC endpoint.

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

from prefect import task, get_run_logger
from prefect.cache_policies import NO_CACHE
from sqlalchemy import text
from sqlalchemy.engine import Engine

# LLM batch size — 32 items per Ollama call reduces per-item overhead ~85%
_LLM_BATCH_SIZE = 32

# Categories the LLM is allowed to return (validated on parse)
_VALID_CATEGORIES: frozenset[str] = frozenset(f"CRS-C{i:02d}" for i in range(1, 51))

# ---------------------------------------------------------------------------
# Parameter extraction
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(
    r"""
    JDA-[A-Z0-9\.\-]+          |  # JDA-SB-V3C-F001
    \b[A-Z]{2,6}[0-9]{3,}\b       # HIS0163, STN0264
    """,
    re.IGNORECASE | re.VERBOSE,
)

_DOC_RE = re.compile(r"JDAW-[A-Z0-9\-]+", re.IGNORECASE)

_PROPERTY_RE = re.compile(
    r"\b(DESIGN_PRESSURE|DESIGN_TEMPERATURE|OPERATING_PRESSURE|OPERATING_TEMPERATURE"
    r"|FLUID_SERVICE|MATERIAL_GRADE|INSULATION_TYPE|HEAT_TRACING|IP_GRADE|EX_CLASS"
    r"|MANUFACTURER|SERIAL_NUMBER|MODEL_NUMBER|[A-Z][A-Z0-9_]{4,})\b",
    re.IGNORECASE,
)


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
) -> str:
    """Build a concise prompt for single-comment classification."""
    text_val = comment.get("comment") or comment.get("group_comment") or ""
    sheet = comment.get("detail_sheet") or "unknown"
    result_str = json.dumps(sql_result[:3], default=str)

    return (
        f"CRS Comment Classification Task\n\n"
        f"Detail sheet: {sheet}\n"
        f"Comment: {text_val}\n"
        f"Extracted params: {json.dumps(params, default=str)}\n"
        f"EDW verification result: {result_str}\n\n"
        f"Task: Classify this engineering CRS comment into ONE category code (CRS-C01..C50).\n"
        f"Categories cover: TAG_DATA, PROPERTY, EQUIPMENT, DOCUMENT, REFERENCE, SAFETY, TOPOLOGY\n\n"
        f"Respond with JSON only:\n"
        f'{{\"category\": \"<CATEGORY>\", \"confidence\": <0.0-1.0>, '
        f'\"response\": \"<brief suggested response>\"}}'
    )


def _call_llm_batch(
    prompts: list[str],
    model: str,
    base_url: str,
    logger: Any = None,
) -> list[dict[str, Any]]:
    """Call Ollama LLM for a batch of prompts.

    Uses langchain_openai.ChatOpenAI pointed at local Ollama endpoint.
    Logs every error explicitly so connection issues are visible in Prefect UI.

    Args:
        prompts: List of prompt strings (max 32 recommended).
        model: Ollama model name (e.g. 'qwen3:32b').
        base_url: Ollama OpenAI-compatible endpoint URL.
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
        api_key="ollama",
        temperature=0.1,
        max_tokens=256,
    )

    results: list[dict[str, Any]] = []
    first_error_logged = False

    for i, prompt in enumerate(prompts):
        try:
            msg = llm.invoke([HumanMessage(content=prompt)])
            raw = msg.content.strip()
            # Extract JSON block if wrapped in markdown
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                cat = parsed.get("category", "OTHER")
                if cat not in _VALID_CATEGORIES:
                    cat = "OTHER"
                results.append({
                    "category":   cat,
                    "confidence": float(parsed.get("confidence", 0.7)),
                    "response":   str(parsed.get("response", "")),
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

    Status mapping:
      confidence >= 0.7 → IN_REVIEW  (valid in crs_comment_status_check)
      confidence <  0.7 → DEFERRED   (valid in crs_comment_status_check)

    Args:
        comments: Batch of unclassified comment dicts (passed from Tier 2).
        engine: SQLAlchemy engine for validation SQL execution.

    Returns:
        List of classified comment dicts.
    """
    logger = get_run_logger()

    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://10.10.10.50:11434/v1")
    ollama_model = os.environ.get("OLLAMA_MODEL", "qwen3:32b")

    # Log endpoint so it's always visible in Prefect UI — helps diagnose connectivity fast
    logger.info("Tier 3: using Ollama endpoint=%s model=%s", ollama_base_url, ollama_model)

    # Load validation queries once per task call
    validation_queries = _load_validation_queries(engine)
    if not validation_queries:
        logger.warning("Tier 3: No active validation queries found in crs_validation_query.")

    results: list[dict[str, Any]] = []

    # Process in batches of 32 for efficient Ollama inference
    for batch_start in range(0, len(comments), _LLM_BATCH_SIZE):
        batch = comments[batch_start : batch_start + _LLM_BATCH_SIZE]
        prompts: list[str] = []
        batch_params: list[dict[str, str | None]] = []

        for comment in batch:
            text_val = comment.get("comment") or comment.get("group_comment") or ""

            params = extract_parameters(text_val)
            if comment.get("from_tag"):
                params["from_tag"] = comment["from_tag"]
            if comment.get("to_tag"):
                params["to_tag"] = comment["to_tag"]
            if comment.get("tag_name"):
                params["tag_name"] = comment["tag_name"]
            if comment.get("property_name"):
                params["property_name"] = comment["property_name"]
            if comment.get("document_number"):
                params["doc_number"] = comment["document_number"]

            vq = _select_query(params, validation_queries)
            sql_result: list[dict[str, Any]] = []
            if vq:
                sql_result = _run_verification(vq, params, engine)

            prompts.append(_build_prompt(comment, params, sql_result))
            batch_params.append(params)

        # Pass logger so connection errors are visible in Prefect UI
        llm_outputs = _call_llm_batch(prompts, ollama_model, ollama_base_url, logger=logger)

        for comment, params, llm_out in zip(batch, batch_params, llm_outputs):
            confidence = llm_out.get("confidence", 0.7)
            status = "IN_REVIEW" if confidence >= 0.7 else "DEFERRED"
            results.append({
                **comment,
                "llm_category":            llm_out["category"],
                "llm_category_confidence": confidence,
                "llm_response":            llm_out.get("response", ""),
                "llm_model_used":          ollama_model,
                "classification_tier":     3,
                "status":                  status,
                "_extracted_params":       params,
                "category_code":           llm_out["category"],
                "category_confidence":     confidence,
            })

    in_review = sum(1 for r in results if r["status"] == "IN_REVIEW")
    deferred = sum(1 for r in results if r["status"] == "DEFERRED")
    logger.info(
        "Tier 3: %d processed — %d in_review, %d deferred (model=%s).",
        len(results), in_review, deferred, ollama_model,
    )
    return results
