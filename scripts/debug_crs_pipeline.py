"""
Debug harness for CRS cascade pipeline (Phase 2 classifier + Phase 3 validator).

Loads comments for a revision, deduplicates to unique generalised groups,
runs classification tier(s), and prints verbose per-group logs.
Optionally continues into Phase 3 validation debug (--phase3 / --category).

No DB writes. No Prefect. Designed for local debugging.

Usage:
    python scripts/debug_crs_pipeline.py --revision A36 --limit 20 --tier 3 --verbose
    python scripts/debug_crs_pipeline.py --revision A36 --reset --tier all
    python scripts/debug_crs_pipeline.py --revision A36 --limit 2 --tier 3 --verbose
    python scripts/debug_crs_pipeline.py --revision-all --limit 5 --tier 0
    python scripts/debug_crs_pipeline.py --revision A36 --limit 5 --tier all --phase3 --verbose
    python scripts/debug_crs_pipeline.py --category CRS-C001
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
        description="Standalone debug harness for CRS cascade pipeline (no Prefect, no DB writes).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--revision", required=False, default=None,
        help="Revision code to process (e.g. A36). Required unless --revision-all or --category is set.",
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
    parser.add_argument(
        "--phase3", action="store_true",
        help="After Phase 2 summary, run Phase 3 validation debug for classified comments.",
    )
    parser.add_argument(
        "--category", default=None,
        help=(
            "Skip Phase 2; load IN_REVIEW comments with this category_code from DB "
            "and run Phase 3 debug directly (e.g. CRS-C001)."
        ),
    )
    args = parser.parse_args()
    if not args.revision_all and args.revision is None and not args.category:
        parser.error("--revision is required unless --revision-all or --category is set.")
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
    log.info("Reset %d classified rows → RECEIVED for revision=%s", result.rowcount, revision)


# ---------------------------------------------------------------------------
# Tier logging helpers
# ---------------------------------------------------------------------------

def _log_tier_results(
    log: logging.Logger,
    tier_num: int | float,
    classified: list[dict[str, Any]],
) -> None:
    """Log per-group summary for Tiers 0-2.5 (no LLM, no prompt).

    Format: [Tier N] group_key='...' → category=CRS-C08 confidence=1.0 status=IN_REVIEW (N rows)
    """
    from etl.tasks.crs_text_generalizer import group_by_generalized  # noqa: PLC0415

    if not classified:
        log.info("[Tier %s] 0 classified.", tier_num)
        return

    # Group by generalised key so we can show unique count
    groups = group_by_generalized(classified)
    for key, rows in groups.items():
        rep = rows[0]
        cat = rep.get("category_code") or rep.get("llm_category") or "?"
        conf = rep.get("category_confidence") or rep.get("llm_category_confidence") or 0.0
        status = rep.get("status", "RECEIVED")
        skip_reason = rep.get("skip_reason") or rep.get("deferred_reason") or ""
        reason_part = f"  reason={skip_reason}" if skip_reason else ""
        log.info(
            "[Tier %s] group_key=%-50r → category=%-8s  confidence=%.2f  status=%-10s%s  (%d row%s)",
            tier_num, key[:50], cat, float(conf), status, reason_part,
            len(rows), "" if len(rows) == 1 else "s",
        )
    log.info("[Tier %s] total: %d classified across %d unique groups.", tier_num, len(classified), len(groups))


# ---------------------------------------------------------------------------
# Tier 3 debug runner
# ---------------------------------------------------------------------------

def _truncate_categories_for_log(user_msg: str) -> str:
    """Return user_msg with the categories list line summarised for log readability.

    The full categories list (229+ entries) floods the console. This replaces
    the long parenthesised line with a head+tail summary — the actual prompt
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

    Calls internal functions directly — does NOT call run_tier3_llm() (Prefect task).
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
        log.warning("Tier 3: no active templates in DB — LLM category hints will be empty.")
    if not queries:
        log.warning("Tier 3: no active validation queries in DB — SQL verification skipped.")

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

        # ── A. Normalised comment ──────────────────────────────────────────────────
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

        # ── B. Parameters + SQL verification ──────────────────────────────────────
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

        # ── C. Domain detection ────────────────────────────────────────────────────
        # Use raw_text for domain detection — normalised text has <prop>/<tag>/<doc>
        # placeholders that corrupt keyword-based domain matching.
        domain          = _detect_comment_domain(raw_text, detail_sheet=rep.get("detail_sheet") or "")
        categories_line = _build_categories_line(templates, domain=domain)
        cat_count       = categories_line.count("CRS-C")
        log.info("  domain:     %s  |  categories_in_prompt=%d", domain, cat_count)

        # ── D. Full prompt (categories list truncated in log to avoid flooding) ────
        system_msg, user_msg = _build_prompt(rep, params, sql_result, categories_line)
        log.info(
            "\n  ── PROMPT ──\n"
            "  [SYSTEM] %s\n"
            "  [USER]\n%s\n"
            "  ── END PROMPT ──",
            system_msg,
            _truncate_categories_for_log(user_msg),  # log only; LLM receives full user_msg
        )

        # ── E. LLM call ────────────────────────────────────────────────────────────
        timeout_val = float(llm_cfg.get("timeout", 30.0))
        log.info("  [%d/%d] calling LLM (timeout=%.0fs)…", idx, total, timeout_val)
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

        # ── F. LLM response ────────────────────────────────────────────────────────
        raw_preview = result["raw_response"]
        if len(raw_preview) > 600:
            raw_preview = raw_preview[:600] + "…"
        log.info(
            "\n  ── LLM RESPONSE ──\n"
            "  raw:     %s\n"
            "  parsed:  category=%-8s  confidence=%.2f\n"
            "  tokens:  prompt=%d  completion=%d  total=%d\n"
            "  ── END RESPONSE ──",
            raw_preview,
            result["category"], result["confidence"],
            result["prompt_tokens"], result["completion_tokens"], result["total_tokens"],
        )

        # ── G. Final status assignment ─────────────────────────────────────────────
        # RULE: ANY category returned with confidence <= 0.30 is forced to
        # NEEDS_NEW_CATEGORY regardless of what the LLM returned as category.
        # Previously only "OTHER + 0.30" triggered this path; specific categories
        # like CRS-C001 at 0.30 silently fell into DEFERRED, masking comments that
        # need human triage (observed in A36 dry-run: 1OO2/7/8 pattern variants).
        _cat  = result["category"]
        _conf = result["confidence"]

        if _conf <= 0.30:
            if _cat != "OTHER":
                log.warning(
                    "  LLM returned category=%s with conf=%.2f (<=0.30) — "
                    "forcing NEEDS_NEW_CATEGORY (expected OTHER at this confidence).",
                    _cat, _conf,
                )
            assigned_status = "NEEDS_NEW_CATEGORY"
        elif _conf >= 0.7:
            assigned_status = "IN_REVIEW"
        else:
            assigned_status = "DEFERRED"

        # CRS-C224: abstract class / no properties in ISM — promote 0.60+ to IN_REVIEW.
        # 1235 rows were stuck in DEFERRED at conf=0.65; this override rescues them.
        if _cat == "CRS-C224" and _conf >= 0.60:
            assigned_status = "IN_REVIEW"
            log.info(
                "  Tier 3: CRS-C224 conf=%.2f >= 0.60 → overriding to IN_REVIEW "
                "(abstract class / no properties in ISM pattern)",
                _conf,
            )

        matched_template = next(
            (t for t in templates if t.get("category") == _cat), None
        )
        template_text = (
            matched_template.get("short_template_text")
            if matched_template
            else "NOT FOUND in templates"
        )
        log.info(
            "\n  ── RESULT ──\n"
            "  category:  %s\n"
            "  template:  %s\n"
            "  response:  %s\n"
            "  status:    %s\n"
            "  ── END RESULT ──",
            _cat,
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
            "category":      _cat,
            "template":      (template_text or "")[:60],
            "llm_response":  result["response"][:80],
            "deferred_reason": "",
        })

    return tier3_results


# ---------------------------------------------------------------------------
# Phase 3 validation debug
# ---------------------------------------------------------------------------

def _run_phase3_debug(
    engine: Any,
    comments: list[dict[str, Any]],
    log: logging.Logger,
    verbose: bool,
) -> list[dict[str, Any]]:
    """Run Phase 3 validation debug for a list of classified comments.

    Args:
        engine: SQLAlchemy engine (read-only — no writes performed).
        comments: List of dicts with keys: id, tag_name, category_code,
                  property_name, document_number, comment.
                  For Phase 2→3 flow: use summary_rows dicts (category_code normalised).
                  For --category mode: rows loaded directly from audit_core.crs_comment.
        log: Logger instance.
        verbose: If True, prints full SQL and evaluates all comments (not just first 5).

    Returns:
        List of per-category summary dicts for the Phase 3 table.
    """
    import json as _json
    from etl.tasks.crs_batch_validator import (  # noqa: PLC0415
        _load_group_queries, _run_group_query, _evaluate_comment,
    )
    from etl.tasks.crs_cascade_evaluator import _substitute  # noqa: PLC0415

    queries = _load_group_queries(engine)
    if not queries:
        print("[PHASE 3] crs_validation_query is empty — run migration_027 seed first.")
        return []

    # Group comments by category_code
    category_map: dict[str, list[dict[str, Any]]] = {}
    for c in comments:
        cat = c.get("category_code") or c.get("llm_category")
        if cat:
            category_map.setdefault(cat, []).append(c)

    p3_summary: list[dict[str, Any]] = []
    sep55 = "═" * 55

    for category_code, cat_comments in category_map.items():
        print(f"\n{sep55}")
        print(f"PHASE 3 — VALIDATION: {category_code}  ({len(cat_comments)} comments)")
        print(sep55)

        cat_queries = [q for q in queries if q["template_category"] == category_code]
        if not cat_queries:
            print(f"  [PHASE 3] No active validation queries for {category_code} — DEFERRED")
            p3_summary.append({
                "category": category_code,
                "queries":  0,
                "passed":   0,
                "failed":   0,
                "deferred": len(cat_comments),
                "tags":     len({c.get("tag_name") for c in cat_comments if c.get("tag_name")}),
            })
            continue

        tag_names = [c["tag_name"] for c in cat_comments if c.get("tag_name")]
        passed_total = failed_total = deferred_total = 0

        for query in cat_queries:
            sql_query      = query["sql_query"]
            has_parameters = bool(query.get("has_parameters"))
            query_code     = query.get("query_code", "?")
            query_name     = query.get("query_name", "")
            strategy       = query.get("evaluation_strategy")

            print(f"\n  [QUERY {query_code}] {query_name}")
            print(f"    evaluation_strategy : {strategy}")
            print(f"    has_parameters      : {has_parameters}")
            print(f"    tag_names sample    : {tag_names[:3]}  (total: {len(tag_names)})")
            if verbose:
                print(f"    SQL:\n{sql_query}")

            try:
                with engine.connect() as conn:
                    rows = _run_group_query(conn, sql_query, tag_names, has_parameters)
            except Exception as exc:
                log.warning("[PHASE 3] Query %s failed: %s", query_code, exc)
                rows = []

            print(f"    rows returned: {len(rows)}")
            preview = _json.dumps(rows[:3], indent=2, default=str)
            print(f"    first 3 rows :\n{preview}")

            # Evaluate per-comment (cap at 5 unless verbose)
            eval_limit = len(cat_comments) if verbose else min(5, len(cat_comments))
            q_passed = q_failed = q_deferred = q_inconclusive = 0
            last_passed_row: dict[str, Any] | None = None
            last_passed_template: str | None = None

            for i, comment in enumerate(cat_comments[:eval_limit], start=1):
                status, result_json = _evaluate_comment(
                    comment, rows,
                    strategy,
                    query.get("expected_result"),
                    query.get("group_by_field"),
                )
                tag = comment.get("tag_name", "?")
                print(f"    comment {i}: tag={tag} → {status}")
                if status == "PASSED":
                    q_passed += 1
                    last_passed_row = result_json
                    last_passed_template = query.get("response_template")
                elif status == "FAILED":
                    q_failed += 1
                elif status == "DEFERRED":
                    q_deferred += 1
                else:
                    q_inconclusive += 1

            print(
                f"    PASSED={q_passed}  FAILED={q_failed}"
                f"  DEFERRED={q_deferred}  INCONCLUSIVE={q_inconclusive}"
            )
            passed_total  += q_passed
            failed_total  += q_failed
            deferred_total += q_deferred

            # Formal response preview for first comment with a PASSED result
            if last_passed_template and cat_comments:
                rep = cat_comments[0]
                formal = _substitute(
                    last_passed_template,
                    rep,
                    last_passed_row,
                    query.get("expected_result"),
                )
                print(
                    f"\n    FORMAL RESPONSE PREVIEW for tag={rep.get('tag_name', '?')}:\n"
                    f"      {formal or '— (template substitution returned empty)'}"
                )
            else:
                print(
                    "\n    FORMAL RESPONSE PREVIEW:"
                    " — (no PASSED validation, response not generated)"
                )

        p3_summary.append({
            "category": category_code,
            "queries":  len(cat_queries),
            "passed":   passed_total,
            "failed":   failed_total,
            "deferred": deferred_total,
            "tags":     len({c.get("tag_name") for c in cat_comments if c.get("tag_name")}),
        })

    return p3_summary


def _print_phase3_summary(rows: list[dict[str, Any]]) -> None:
    """Print Phase 3 validation summary table."""
    sep  = "═" * 55
    line = "─" * 55
    hdr  = (
        f"  {'Category':<12}  {'Queries':>7}  {'PASSED':>6}"
        f"  {'FAILED':>6}  {'DEFERRED':>8}  {'Tags':>4}"
    )
    print(f"\n{sep}")
    print("PHASE 3 VALIDATION SUMMARY")
    print(line)
    print(hdr)
    print(line)
    for r in rows:
        print(
            f"  {r['category']:<12}  {r['queries']:>7}  {r['passed']:>6}"
            f"  {r['failed']:>6}  {r['deferred']:>8}  {r['tags']:>4}"
        )
    print(f"{sep}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for the CRS debug pipeline harness."""
    args = parse_args()
    setup_logging(args.verbose)
    log = logging.getLogger("debug_crs")

    if args.dry_run:
        args.tier = "all"
        log.info("DRY-RUN mode: full Tier 0→3 cascade, no DB writes.")

    # Lazy imports — deferred until after env vars are set above, so Prefect
    # @task decorators don't trigger an API server lookup at module load time.
    log.info("Importing ETL modules…")
    from etl.tasks.crs_helpers import get_engine, load_received_comments  # noqa: PLC0415
    from etl.tasks.crs_text_generalizer import group_by_generalized  # noqa: PLC0415
    from etl.tasks.crs_tier0_prefilter import run_tier0  # noqa: PLC0415
    from etl.tasks.crs_tier1_template_matcher import run_tier1  # noqa: PLC0415
    from etl.tasks.crs_tier2_keyword_classifier import run_tier2  # noqa: PLC0415
    from etl.tasks.crs_tier25_benchmark_matcher import run_tier25_benchmark  # noqa: PLC0415
    log.info("ETL modules loaded.")

    log.info("Starting CRS debug pipeline with args: %s", args)

    engine = get_engine()

    # ── --category mode: skip Phase 2, go straight to Phase 3 ────────────────
    if args.category and not args.revision and not args.revision_all:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            db_rows = conn.execute(_text("""
                SELECT id, tag_name, category_code, property_name,
                       document_number, comment
                FROM audit_core.crs_comment
                WHERE status        = 'IN_REVIEW'
                  AND category_code = :cat
                  AND object_status = 'Active'
            """), {"cat": args.category}).fetchall()
        p3_comments = [dict(r._mapping) for r in db_rows]
        log.info(
            "Phase 3 mode: loaded %d IN_REVIEW comments for %s",
            len(p3_comments), args.category,
        )
        if not p3_comments:
            log.warning("No IN_REVIEW comments found for category=%s.", args.category)
            return
        p3_summary = _run_phase3_debug(engine, p3_comments, log, args.verbose)
        _print_phase3_summary(p3_summary)
        return

    # ── 1. Optional reset ──────────────────────────────────────────────────────
    if args.reset:
        if args.revision_all:
            log.error("--reset requires --revision (cannot reset all revisions at once).")
            sys.exit(1)
        _reset_classification(engine, args.revision, log)

    # ── 2. Load comments ───────────────────────────────────────────────────────
    revision_label = "ALL" if args.revision_all else args.revision
    comments = load_received_comments(
        limit=0,   # load all; slice after dedup below
        engine=engine,
        revision_filter=None if args.revision_all else args.revision,
    )
    log.info("Loaded %d RECEIVED comments  (revision=%s)", len(comments), revision_label)

    if not comments:
        log.warning("No RECEIVED comments found — nothing to process.")
        return

    # ── 3. Deduplicate to unique generalised groups ────────────────────────────
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

    # ── 4. Run tiers ───────────────────────────────────────────────────────────
    remaining: list[dict[str, Any]] = list(comments)
    classified: list[dict[str, Any]] = []
    run_tier = args.tier.lower()

    # Tier 0 always runs — mandatory pre-filter regardless of --tier flag.
    # Mirrors production flow where Tier 0 always precedes all other tiers.
    log.info("── Tier 0: pre-filter ──  (%d comments)", len(remaining))
    remaining, t0 = run_tier0(remaining, engine)
    classified.extend(t0)
    _log_tier_results(log, 0, t0)
    log.info("Tier 0: %d handled, %d remaining.", len(t0), len(remaining))

    if run_tier in ("1", "2", "all"):
        log.info("── Tier 1: template KB match ──  (%d comments)", len(remaining))
        remaining, t1 = run_tier1(remaining, engine)
        classified.extend(t1)
        _log_tier_results(log, 1, t1)
        log.info("Tier 1: %d classified, %d remaining.", len(t1), len(remaining))

    if run_tier in ("2", "all"):
        log.info("── Tier 2: keyword classifier ──  (%d comments)", len(remaining))
        remaining, t2 = run_tier2(remaining)
        classified.extend(t2)
        _log_tier_results(log, 2, t2)
        log.info("Tier 2: %d classified, %d remaining.", len(t2), len(remaining))

    if run_tier in ("2", "all"):
        log.info("── Tier 2.5: benchmark matcher ──  (%d comments)", len(remaining))
        remaining, t25_classified = run_tier25_benchmark(remaining, engine)
        classified.extend(t25_classified)
        # Use 2.5 as tier label to distinguish from Tier 2 in logs
        _log_tier_results(log, 2.5, t25_classified)
        log.info("Tier 2.5: %d classified, %d remaining.", len(t25_classified), len(remaining))

    tier3_summary: list[dict[str, Any]] = []
    if run_tier in ("3", "all"):
        if remaining:
            log.info("── Tier 3: LLM classifier ──  (%d comments remaining)", len(remaining))
            tier3_summary = _run_tier3_debug(remaining, engine, args, log)
        else:
            log.info("── Tier 3: skipped (no comments remaining after earlier tiers).")

    # ── 5. Summary table ───────────────────────────────────────────────────────
    # Build rows: Tier 0 skipped + Tier 1/2/2.5 classified + Tier 3 results
    summary_rows: list[dict[str, Any]] = []

    # Tiers 0-2.5: extract from classified list
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

    # Count stats.
    # n_classified: groups that received a definitive IN_REVIEW assignment.
    # Excludes DEFERRED, NEEDS_NEW_CATEGORY, ERROR, RECEIVED, TAGINACTIVE and
    # any unknown "?" status — these all require further action.
    _UNRESOLVED_STATUSES = frozenset({
        "DEFERRED", "NEEDS_NEW_CATEGORY", "ERROR", "?", "RECEIVED", "TAGINACTIVE",
    })
    total_loaded   = len(comments)
    total_groups   = len(_gbg(comments))
    n_deferred     = sum(r["row_count"] for r in summary_rows if r["status"] == "DEFERRED")
    n_needs_new    = sum(r["row_count"] for r in summary_rows if r["status"] == "NEEDS_NEW_CATEGORY")
    n_classified   = sum(
        r["row_count"] for r in summary_rows if r["status"] not in _UNRESOLVED_STATUSES
    )

    # Build category → short description lookup (DB first, fallback to hardcoded)
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

    # ── Dynamic comment column width ──────────────────────────────────────────
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

    sep  = "═" * total_width
    line = "─" * total_width
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
                    desc_short = desc[:max_desc - 1] + "…" if len(desc) > max_desc - 1 else desc
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
        f"TOTAL: {total_loaded} rows loaded → {total_groups} unique groups"
        f" → {n_deferred} rows DEFERRED"
        f" → {n_needs_new} rows NEEDS_NEW_CATEGORY"
        f" → {n_classified} rows classified (IN_REVIEW)"
    )
    print(f"{sep}\n")

    log.info(
        "DONE.  %d total input rows → %d classified (IN_REVIEW)"
        "  |  %d rows DEFERRED  |  --tier=%s",
        total_loaded, n_classified, n_deferred, args.tier,
    )

    if args.dry_run:
        log.info("DRY-RUN complete. No DB writes performed.")

    # ── 6. Optional Phase 3 validation debug ──────────────────────────────────
    if args.phase3:
        # Normalise: summary_rows use "category" key; Phase 3 needs "category_code"
        p3_comments = [
            {**r, "category_code": r.get("category_code") or r.get("category")}
            for r in summary_rows
            if r.get("status") == "IN_REVIEW"
        ]
        if p3_comments:
            p3_summary = _run_phase3_debug(engine, p3_comments, log, args.verbose)
            _print_phase3_summary(p3_summary)
        else:
            log.info("--phase3: no IN_REVIEW comments in Phase 2 results — nothing to validate.")


if __name__ == "__main__":
    main()
