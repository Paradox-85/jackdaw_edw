"""
Debug harness for CRS cascade classifier.

Loads comments for a revision, deduplicates to unique generalised groups,
runs classification tier(s), and prints verbose per-group logs.

No DB writes. No Prefect. Designed for local debugging.

Usage:
    python scripts/debug_crs_classifier.py --revision A36 --limit 20 --tier 3 --verbose
    python scripts/debug_crs_classifier.py --revision A36 --reset --tier all
    python scripts/debug_crs_classifier.py --revision A36 --limit 2 --tier 3 --verbose
    python scripts/debug_crs_classifier.py --revision-all --limit 5 --tier 0
"""
from __future__ import annotations

import os

# Suppress Prefect API calls and telemetry banner before any other imports.
# Without these, importing etl.tasks.* modules that use @task decorator
# triggers a Prefect server DNS/TCP lookup that hangs ~30s when run outside
# the container network.
os.environ.setdefault("PREFECT_API_URL", "")
os.environ.setdefault("DO_NOT_TRACK", "1")
os.environ.setdefault("PREFECT_SERVER_ANALYTICS_ENABLED", "false")
os.environ.setdefault("PREFECT_LOGGING_TO_API_WHEN_MISSING_FLOW", "ignore")

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Any

# Bootstrap sys.path so local etl.* imports work when run from any directory
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Standalone debug harness for CRS cascade classifier (no Prefect, no DB writes).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--revision", required=False, default=None,
        help="Revision code to process (e.g. A36). Required unless --revision-all is set.",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Max unique groups to process after dedup (0 = all).",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Delete existing classification results for this revision before run.",
    )
    parser.add_argument(
        "--tier", default="all",
        choices=["0", "1", "2", "3", "all"],
        help="Which tier to run (lower tiers always run as pre-filter for higher ones).",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable DEBUG logging (full prompts, raw LLM output).",
    )
    parser.add_argument(
        "--revision-all", action="store_true",
        help="Load all RECEIVED comments regardless of revision.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help=(
            "Run full Tier 0→3 cascade and print summary table. "
            "No DB writes. Overrides --tier (always runs all tiers)."
        ),
    )
    args = parser.parse_args()
    if not args.revision_all and args.revision is None:
        parser.error("--revision is required unless --revision-all is set.")
    return args


def setup_logging(verbose: bool) -> None:
    """Configure root logger."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quieten noisy third-party loggers regardless of verbose flag
    for noisy in ("httpx", "httpcore", "urllib3", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Reset helper
# ---------------------------------------------------------------------------

def _reset_classification(engine: Any, revision: str, log: logging.Logger) -> None:
    """Delete existing classification for the given revision (sets status back to RECEIVED).

    Args:
        engine: SQLAlchemy engine.
        revision: Revision code to reset.
        log: Logger instance.
    """
    from sqlalchemy import text

    with engine.begin() as conn:
        result = conn.execute(
            text("""
                UPDATE audit_core.crs_comment
                SET status               = 'RECEIVED',
                    category_code        = NULL,
                    category_confidence  = NULL,
                    classification_tier  = NULL,
                    llm_category         = NULL,
                    llm_category_confidence = NULL,
                    llm_response         = NULL,
                    llm_model_used       = NULL
                WHERE revision = :rev
                  AND status != 'RECEIVED'
            """),
            {"rev": revision},
        )
    log.info("Reset %d classified rows \u2192 RECEIVED for revision=%s", result.rowcount, revision)


# ---------------------------------------------------------------------------
# Tier logging helpers
# ---------------------------------------------------------------------------

def _log_tier_results(
    log: logging.Logger,
    tier_num: int,
    classified: list[dict[str, Any]],
) -> None:
    """Log per-group summary for Tiers 0-2 (no LLM, no prompt).

    Format: [Tier N] group_key='...' \u2192 category=CRS-C08 confidence=1.0 status=IN_REVIEW (N rows)
    """
    from etl.tasks.crs_text_generalizer import group_by_generalized  # noqa: PLC0415

    if not classified:
        log.info("[Tier %d] 0 classified.", tier_num)
        return

    # Group by generalised key so we can show unique count
    groups = group_by_generalized(classified)
    for key, rows in groups.items():
        rep = rows[0]
        cat = rep.get("category_code") or rep.get("llm_category") or "?"
        conf = rep.get("category_confidence") or rep.get("llm_category_confidence") or 0.0
        status = rep.get("status", "RECEIVED")
        log.info(
            "[Tier %d] group_key=%-50r \u2192 category=%-8s  confidence=%.2f  status=%-10s  (%d row%s)",
            tier_num, key[:50], cat, float(conf), status,
            len(rows), "" if len(rows) == 1 else "s",
        )
    log.info("[Tier %d] total: %d classified across %d unique groups.", tier_num, len(classified), len(groups))


# ---------------------------------------------------------------------------
# Tier 3 debug runner
# ---------------------------------------------------------------------------

def _truncate_categories_for_log(user_msg: str) -> str:
    """Return user_msg with the categories list line summarised for log readability.

    The full categories list (229+ entries) floods the console. This replaces
    the long parenthesised line with a head+tail summary \u2014 the actual prompt
    passed to the LLM is never modified.

    Args:
        user_msg: Full user prompt string.

    Returns:
        Modified string with categories line replaced by a summary,
        or the original string if no categories line is found.
    """
    lines = user_msg.splitlines()
    result_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("(CRS-C") or (stripped.startswith("(") and "CRS-C" in stripped):
            # Parse out individual category entries: "CRS-Cxxx=..."
            import re as _re
            entries = _re.findall(r"CRS-C\d+=[^,)]+", line)
            count = len(entries)
            if count > 6:
                head = ", ".join(entries[:3])
                tail = ", ".join(entries[-3:])
                result_lines.append(f"({head}, ... {tail} [{count} total categories])")
            else:
                result_lines.append(line)
        else:
            result_lines.append(line)
    return "\n".join(result_lines)


def _run_tier3_debug(
    comments: list[dict[str, Any]],
    engine: Any,
    args: argparse.Namespace,
    log: logging.Logger,
) -> list[dict[str, Any]]:
    """Run Tier 3 LLM classification with verbose per-group debug output.

    Calls internal functions directly \u2014 does NOT call run_tier3_llm() (Prefect task).
    No DB writes are performed.

    Args:
        comments: Unclassified comment dicts reaching Tier 3.
        engine: SQLAlchemy engine.
        args: Parsed CLI args (for verbose flag).
        log: Logger instance.

    Returns:
        List of result dicts for summary table, one per unique group processed.
    """
    from etl.tasks.crs_tier3_llm_classifier import (  # noqa: PLC0415
        _build_prompt,
        _call_llm_single_debug,
        _build_categories_line,
        _load_crs_templates,
        _load_validation_queries,
        _select_query,
        _run_verification,
        extract_parameters,
        _detect_comment_domain,
        _resolve_llm_url,
    )
    from etl.tasks.crs_text_generalizer import generalize_comment, group_by_generalized  # noqa: PLC0415
    from etl.tasks.common import load_config, get_llm_config  # noqa: PLC0415

    llm_cfg  = get_llm_config(load_config())
    base_url = _resolve_llm_url(llm_cfg)
    model    = os.environ.get("OLLAMA_MODEL") or llm_cfg["model"]
    api_key  = os.environ.get("OLLAMA_API_KEY") or llm_cfg.get("api_key", "none")

    log.info("Tier 3 LLM: endpoint=%s  model=%s", base_url, model)

    queries   = _load_validation_queries(engine)
    templates = _load_crs_templates(engine)

    if not templates:
        log.warning("Tier 3: no active templates in DB \u2014 LLM category hints will be empty.")
    if not queries:
        log.warning("Tier 3: no active validation queries in DB \u2014 SQL verification skipped.")

    from etl.tasks.crs_tier0_prefilter import is_multi_comment_group  # noqa: PLC0415

    groups = group_by_generalized(comments)
    total  = len(groups)

    tier3_results: list[dict[str, Any]] = []

    for idx, (key, rows) in enumerate(groups.items(), start=1):
        # Prefer row with specific comment (differs from group_comment sheet header).
        rep = next(
            (r for r in rows
             if r.get("comment") and r.get("comment") != r.get("group_comment")),
            rows[0],
        )
        raw_text = rep.get("comment") or rep.get("group_comment") or ""
        rep = {**rep, "comment": raw_text}   # normalise: always use "comment" key
        is_multi = is_multi_comment_group(rep)

        # \u2500\u2500 A. Normalised comment \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        normalised = generalize_comment(raw_text)
        log.info(
            "\n%s\n[Group %d/%d]  (%d row%s)  multi=%s\n"
            "  raw:        %s\n"
            "  normalised: %s",
            "=" * 70, idx, total,
            len(rows), "" if len(rows) == 1 else "s",
            "Y" if is_multi else "N",
            raw_text, normalised,
        )

        # \u2500\u2500 B. Parameters + SQL verification \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        params = extract_parameters(raw_text)
        # Override with structured fields from DB row where available
        field_map = [
            ("from_tag",        "from_tag"),
            ("to_tag",          "to_tag"),
            ("tag_name",        "tag_name"),
            ("property_name",   "property_name"),
            ("document_number", "doc_number"),
        ]
        for src_key, param_key in field_map:
            if rep.get(src_key):
                params[param_key] = rep[src_key]

        vq         = _select_query(params, queries)
        sql_result = _run_verification(vq, params, engine) if vq else []

        log.info("  params:     %s", params)
        log.info("  sql_query:  %s", vq["query_code"] if vq else "None")
        log.info("  sql_result: %s", sql_result[:2])

        # \u2500\u2500 C. Domain detection \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        # Use raw_text for domain detection \u2014 normalised text has <prop>/<tag>/<doc>
        # placeholders that corrupt keyword-based domain matching.
        domain          = _detect_comment_domain(raw_text, detail_sheet=rep.get("detail_sheet") or "")
        categories_line = _build_categories_line(templates, domain=domain)
        cat_count       = categories_line.count("CRS-C")
        log.info("  domain:     %s  |  categories_in_prompt=%d", domain, cat_count)

        # \u2500\u2500 D. Full prompt (categories list truncated in log to avoid flooding) \u2500\u2500\u2500\u2500
        system_msg, user_msg = _build_prompt(rep, params, sql_result, categories_line)
        log.info(
            "\n  \u2500\u2500 PROMPT \u2500\u2500\n"
            "  [SYSTEM] %s\n"
            "  [USER]\n%s\n"
            "  \u2500\u2500 END PROMPT \u2500\u2500",
            system_msg,
            _truncate_categories_for_log(user_msg),  # log only; LLM receives full user_msg
        )

        # \u2500\u2500 E. LLM call \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        timeout_val = float(llm_cfg.get("timeout", 30.0))
        log.info("  [%d/%d] calling LLM (timeout=%.0fs)\u2026", idx, total, timeout_val)
        _t0 = time.monotonic()
        result = _call_llm_single_debug(
            (system_msg, user_msg),
            model,
            base_url,
            api_key,
            temperature=float(llm_cfg.get("temperature", 0.1)),
            max_tokens=int(llm_cfg.get("max_tokens", 512)),
            timeout=timeout_val,
        )
        log.info("  [%d/%d] LLM responded in %.1fs", idx, total, time.monotonic() - _t0)

        if result["error"]:
            log.error("  LLM ERROR: %s", result["error"])
            tier3_results.append({
                "group_key":     key[:60],
                "raw_text":      raw_text,
                "is_multi":      is_multi,
                "row_count":     len(rows),
                "tier":          3,
                "status":        "ERROR",
                "category":      "ERROR",
                "template":      "N/A",
                "llm_response":  result["error"][:80],
                "deferred_reason": "",
            })
            continue

        # \u2500\u2500 F. LLM response \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        raw_preview = result["raw_response"]
        if len(raw_preview) > 600:
            raw_preview = raw_preview[:600] + "\u2026"
        log.info(
            "\n  \u2500\u2500 LLM RESPONSE \u2500\u2500\n"
            "  raw:     %s\n"
            "  parsed:  category=%-8s  confidence=%.2f\n"
            "  tokens:  prompt=%d  completion=%d  total=%d\n"
            "  \u2500\u2500 END RESPONSE \u2500\u2500",
            raw_preview,
            result["category"], result["confidence"],
            result["prompt_tokens"], result["completion_tokens"], result["total_tokens"],
        )

        # \u2500\u2500 G. Final template + assigned status \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        matched_template = next(
            (t for t in templates if t.get("category") == result["category"]), None
        )
        _cat = result["category"]
        _conf = result["confidence"]
        if _cat == "OTHER" and _conf <= 0.30:
            assigned_status = "NEEDS_NEW_CATEGORY"
        elif _conf >= 0.7:
            assigned_status = "IN_REVIEW"
        else:
            assigned_status = "DEFERRED"
        template_text = (
            matched_template.get("short_template_text")
            if matched_template
            else "NOT FOUND in templates"
        )
        log.info(
            "\n  \u2500\u2500 RESULT \u2500\u2500\n"
            "  category:  %s\n"
            "  template:  %s\n"
            "  response:  %s\n"
            "  status:    %s\n"
            "  \u2500\u2500 END RESULT \u2500\u2500",
            result["category"],
            template_text,
            result["response"],
            assigned_status,
        )

        tier3_results.append({
            "group_key":     key[:60],
            "raw_text":      raw_text,
            "is_multi":      is_multi,
            "row_count":     len(rows),
            "tier":          3,
            "status":        assigned_status,
            "category":      result["category"],
            "template":      (template_text or "")[:60],
            "llm_response":  result["response"][:80],
            "deferred_reason": "",
        })

    return tier3_results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for the CRS debug harness."""
    args = parse_args()
    setup_logging(args.verbose)
    log = logging.getLogger("debug_crs")

    if args.dry_run:
        args.tier = "all"
        log.info("DRY-RUN mode: full Tier 0→3 cascade, no DB writes.")

    # Lazy imports \u2014 deferred until after env vars are set above, so Prefect
    # @task decorators don't trigger an API server lookup at module load time.
    log.info("Importing ETL modules\u2026")
    from etl.tasks.crs_helpers import get_engine, load_received_comments  # noqa: PLC0415
    from etl.tasks.crs_text_generalizer import group_by_generalized  # noqa: PLC0415
    from etl.tasks.crs_tier0_prefilter import run_tier0  # noqa: PLC0415
    from etl.tasks.crs_tier1_template_matcher import run_tier1  # noqa: PLC0415
    from etl.tasks.crs_tier2_keyword_classifier import run_tier2  # noqa: PLC0415
    from etl.tasks.crs_tier25_benchmark_matcher import run_tier25_benchmark  # noqa: PLC0415
    log.info("ETL modules loaded.")

    log.info("Starting CRS debug classifier with args: %s", args)

    engine = get_engine()

    # \u2500\u2500 1. Optional reset \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    if args.reset:
        if args.revision_all:
            log.error("--reset requires --revision (cannot reset all revisions at once).")
            sys.exit(1)
        _reset_classification(engine, args.revision, log)

    # \u2500\u2500 2. Load comments \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    revision_label = "ALL" if args.revision_all else args.revision
    comments = load_received_comments(
        limit=0,   # load all; slice after dedup below
        engine=engine,
        revision_filter=None if args.revision_all else args.revision,
    )
    log.info("Loaded %d RECEIVED comments  (revision=%s)", len(comments), revision_label)

    if not comments:
        log.warning("No RECEIVED comments found \u2014 nothing to process.")
        return

    # \u2500\u2500 3. Deduplicate to unique generalised groups \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    groups     = group_by_generalized(comments)
    unique_keys = list(groups.keys())
    log.info(
        "Unique generalised groups: %d  (from %d total comments)",
        len(unique_keys), len(comments),
    )

    # Apply --limit to unique groups AFTER dedup (not to raw comments)
    if args.limit > 0:
        unique_keys = unique_keys[:args.limit]
        groups      = {k: groups[k] for k in unique_keys}
        # Flatten back to a flat list for tier functions
        comments = [row for rows in groups.values() for row in rows]
        log.info(
            "Limiting to %d unique groups  (%d comments after limit applied)",
            len(unique_keys), len(comments),
        )

    # \u2500\u2500 4. Run tiers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    remaining: list[dict[str, Any]] = list(comments)
    classified: list[dict[str, Any]] = []
    run_tier = args.tier.lower()

    # Tier 0 always runs \u2014 mandatory pre-filter regardless of --tier flag.
    # Mirrors production flow where Tier 0 always precedes all other tiers.
    log.info("\u2500\u2500 Tier 0: pre-filter \u2500\u2500  (%d comments)", len(remaining))
    remaining, t0 = run_tier0(remaining, engine)
    classified.extend(t0)
    _log_tier_results(log, 0, t0)
    log.info("Tier 0: %d handled, %d remaining.", len(t0), len(remaining))

    if run_tier in ("1", "2", "all"):
        log.info("\u2500\u2500 Tier 1: template KB match \u2500\u2500  (%d comments)", len(remaining))
        remaining, t1 = run_tier1(remaining, engine)
        classified.extend(t1)
        _log_tier_results(log, 1, t1)
        log.info("Tier 1: %d classified, %d remaining.", len(t1), len(remaining))

    if run_tier in ("2", "all"):
        log.info("\u2500\u2500 Tier 2: keyword classifier \u2500\u2500  (%d comments)", len(remaining))
        remaining, t2 = run_tier2(remaining)
        classified.extend(t2)
        _log_tier_results(log, 2, t2)
        log.info("Tier 2: %d classified, %d remaining.", len(t2), len(remaining))

    if run_tier in ("2", "all"):
        log.info("\u2500\u2500 Tier 2.5: benchmark matcher \u2500\u2500  (%d comments)", len(remaining))
        t25_classified, remaining = run_tier25_benchmark(remaining, engine)
        classified.extend(t25_classified)
        _log_tier_results(log, 2, t25_classified)  # reuse existing helper, tier label shown as 2
        log.info("Tier 2.5: %d classified, %d remaining.", len(t25_classified), len(remaining))

    tier3_summary: list[dict[str, Any]] = []
    if run_tier in ("3", "all"):
        if remaining:
            log.info("\u2500\u2500 Tier 3: LLM classifier \u2500\u2500  (%d comments remaining)", len(remaining))
            tier3_summary = _run_tier3_debug(remaining, engine, args, log)
        else:
            log.info("\u2500\u2500 Tier 3: skipped (no comments remaining after earlier tiers).")

    # \u2500\u2500 5. Summary table \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    # Build rows: Tier 0 skipped + Tier 1/2 classified + Tier 3 results
    summary_rows: list[dict[str, Any]] = []

    # Tiers 0-2: extract from classified list
    from etl.tasks.crs_text_generalizer import group_by_generalized as _gbg  # noqa: PLC0415
    from etl.tasks.crs_tier0_prefilter import is_multi_comment_group as _imc  # noqa: PLC0415
    for grp_key, grp_rows in _gbg(classified).items():
        rep = grp_rows[0]
        raw = rep.get("comment") or rep.get("group_comment") or ""
        summary_rows.append({
            "group_key":     grp_key[:60],
            "raw_text":      raw,
            "is_multi":      _imc(rep),
            "row_count":     len(grp_rows),
            "tier":          rep.get("classification_tier") or 0,
            "status":        rep.get("status", "?"),
            "category":      rep.get("category_code") or rep.get("llm_category") or "N/A",
            "template":      "",
            "llm_response":  "",
            "deferred_reason": rep.get("skip_reason") or rep.get("deferred_reason") or "",
        })

    # Tier 3 results appended after
    summary_rows.extend(tier3_summary)

    # Count stats
    total_loaded   = len(comments)
    total_groups   = len(_gbg(comments))
    n_deferred     = sum(1 for r in summary_rows if r["status"] == "DEFERRED")
    n_needs_new    = sum(1 for r in summary_rows if r["status"] == "NEEDS_NEW_CATEGORY")
    n_classified   = sum(1 for r in summary_rows
                         if r["status"] not in ("DEFERRED", "NEEDS_NEW_CATEGORY", "ERROR", "?"))

    # Build category \u2192 short description lookup (DB first, fallback to hardcoded)
    cat_desc: dict[str, str] = {}
    try:
        from etl.tasks.crs_tier3_llm_classifier import (  # noqa: PLC0415
            _load_crs_templates,
            _FALLBACK_CATEGORIES,
        )
        db_templates = _load_crs_templates(engine)
        for t in db_templates:
            cat = t.get("category")
            txt = t.get("short_template_text")
            if cat and txt:
                cat_desc[cat] = txt
        for cat, desc in _FALLBACK_CATEGORIES.items():
            if cat not in cat_desc:
                cat_desc[cat] = desc
    except Exception as e:
        log.warning("Could not load category descriptions: %s", e)

    # \u2500\u2500 Dynamic comment column width \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    # Calculate width based on the longest comment in result set.
    # Floor=30 so short comments still look reasonable.
    # Cap=120 to avoid wrapping on standard 200-char terminals.
    _COMMENT_COL_MIN  = 30
    _COMMENT_COL_MAX  = 120
    comment_col_width = max(
        _COMMENT_COL_MIN,
        min(
            _COMMENT_COL_MAX,
            max((len(r["raw_text"].replace("\n", " ")) for r in summary_rows), default=_COMMENT_COL_MIN),
        ),
    )

    # Fixed columns: '#'(3) + Tier(4) + Status(10) + Category(52) + Rows(5) + M(1)
    # Separators: 2sp*6 = 12.  Total fixed = 3+4+10+52+5+1+12 = 87
    _FIXED_WIDTH = 87
    total_width  = _FIXED_WIDTH + comment_col_width

    sep  = "\u2550" * total_width
    line = "\u2500" * total_width
    hdr  = (
        f"{'#':>3}  {'Tier':>4}  {'Status':<10}  {'Category':<52}  "
        f"{'Rows':>5}  {'M':>1}  {'Comment':<{comment_col_width}}"
    )
    print(f"\n{sep}")
    print("CLASSIFICATION SUMMARY")
    print(line)
    print(hdr)
    print(line)
    for i, r in enumerate(summary_rows, start=1):
        if r["status"] == "NEEDS_NEW_CATEGORY":
            llm_hint = (r.get("llm_response") or r.get("template") or "")[:28]
            cat_cell = f"? UNMATCHED  {llm_hint}"
        elif r["status"] == "DEFERRED" and r["tier"] == 0 and r.get("deferred_reason"):
            cat_cell = f"N/A ({r['deferred_reason']})"
        else:
            cat_code = r["category"]
            desc = cat_desc.get(cat_code, "")
            if desc:
                max_desc = 52 - len(cat_code) - 1  # 1 for space separator
                if max_desc > 4:
                    desc_short = desc[:max_desc - 1] + "\u2026" if len(desc) > max_desc - 1 else desc
                    cat_cell = f"{cat_code} {desc_short}"
                else:
                    cat_cell = cat_code
            else:
                cat_cell = cat_code

        _raw = r["raw_text"].replace("\n", " ")
        comment_col = (
            _raw[: comment_col_width - 1] + "…"
            if len(_raw) > comment_col_width
            else _raw
        )
        print(
            f"{i:>3}  {r['tier']:>4}  {r['status']:<10}  {cat_cell:<52}"
            f"  {r['row_count']:>5}  {'Y' if r['is_multi'] else 'N':>1}  {comment_col}"
        )
    print(line)
    print(
        f"TOTAL: {total_loaded} loaded \u2192 {total_groups} unique groups selected"
        f" \u2192 {n_deferred} DEFERRED"
        f" \u2192 {n_needs_new} NEEDS_NEW_CATEGORY"
        f" \u2192 {n_classified} classified by LLM"
    )
    print(f"{sep}\n")

    log.info(
        "DONE.  %d total input comments \u2192 %d classified"
        "  |  %d DEFERRED  |  --tier=%s",
        total_loaded, n_classified, n_deferred, args.tier,
    )

    if args.dry_run:
        log.info("DRY-RUN complete. No DB writes performed.")


if __name__ == "__main__":
    main()
