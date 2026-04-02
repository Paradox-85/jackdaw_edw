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
    log.info("Reset %d classified rows → RECEIVED for revision=%s", result.rowcount, revision)


# ---------------------------------------------------------------------------
# Tier logging helpers
# ---------------------------------------------------------------------------

def _log_tier_results(
    log: logging.Logger,
    tier_num: int,
    classified: list[dict[str, Any]],
) -> None:
    """Log per-group summary for Tiers 0-2 (no LLM, no prompt).

    Format: [Tier N] group_key='...' → category=CRS-C08 confidence=1.0 status=IN_REVIEW (N rows)
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
            "[Tier %d] group_key=%-50r → category=%-8s  confidence=%.2f  status=%-10s  (%d row%s)",
            tier_num, key[:50], cat, float(conf), status,
            len(rows), "" if len(rows) == 1 else "s",
        )
    log.info("[Tier %d] total: %d classified across %d unique groups.", tier_num, len(classified), len(groups))


# ---------------------------------------------------------------------------
# Tier 3 debug runner
# ---------------------------------------------------------------------------

def _run_tier3_debug(
    comments: list[dict[str, Any]],
    engine: Any,
    args: argparse.Namespace,
    log: logging.Logger,
) -> None:
    """Run Tier 3 LLM classification with verbose per-group debug output.

    Calls internal functions directly — does NOT call run_tier3_llm() (Prefect task).
    No DB writes are performed.

    Args:
        comments: Unclassified comment dicts reaching Tier 3.
        engine: SQLAlchemy engine.
        args: Parsed CLI args (for verbose flag).
        log: Logger instance.
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

    groups = group_by_generalized(comments)
    total  = len(groups)

    for idx, (key, rows) in enumerate(groups.items(), start=1):
        # Prefer row with specific comment (differs from group_comment sheet header).
        rep = next(
            (r for r in rows
             if r.get("comment") and r.get("comment") != r.get("group_comment")),
            rows[0],
        )
        raw_text = rep.get("comment") or rep.get("group_comment") or ""

        # ── A. Normalised comment ──────────────────────────────────────────
        normalised = generalize_comment(raw_text)
        log.info(
            "\n%s\n[Group %d/%d]  (%d row%s)\n"
            "  raw:        %s\n"
            "  normalised: %s",
            "=" * 70, idx, total,
            len(rows), "" if len(rows) == 1 else "s",
            raw_text, normalised,
        )

        # ── B. Parameters + SQL verification ──────────────────────────────
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

        # ── C. Domain detection ────────────────────────────────────────────
        # Use raw_text for domain detection — normalised text has <prop>/<tag>/<doc>
        # placeholders that corrupt keyword-based domain matching.
        domain          = _detect_comment_domain(raw_text)
        # Pass detected domain — mirrors production two_pass=True behaviour.
        # Helps validate domain filtering logic during development.
        categories_line = _build_categories_line(templates, domain=domain)
        cat_count       = categories_line.count("CRS-C")
        log.info("  domain:     %s  |  categories_in_prompt=%d", domain, cat_count)

        # ── D. Full prompt (always shown — verbose adds no extra here) ─────
        system_msg, user_msg = _build_prompt(rep, params, sql_result, categories_line)
        log.info(
            "\n  ── PROMPT ──\n"
            "  [SYSTEM] %s\n"
            "  [USER]\n%s\n"
            "  ── END PROMPT ──",
            system_msg, user_msg,
        )

        # ── E. LLM call ───────────────────────────────────────────────────
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
            continue

        # ── F. LLM response ───────────────────────────────────────────────
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

        # ── G. Final template + assigned status ───────────────────────────
        matched_template = next(
            (t for t in templates if t.get("category") == result["category"]), None
        )
        assigned_status = "IN_REVIEW" if result["confidence"] >= 0.7 else "DEFERRED"
        log.info(
            "\n  ── RESULT ──\n"
            "  category:  %s\n"
            "  template:  %s\n"
            "  response:  %s\n"
            "  status:    %s\n"
            "  ── END RESULT ──",
            result["category"],
            matched_template.get("short_template_text") if matched_template else "NOT FOUND in templates",
            result["response"],
            assigned_status,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for the CRS debug harness."""
    args = parse_args()
    setup_logging(args.verbose)
    log = logging.getLogger("debug_crs")

    # Lazy imports — deferred until after env vars are set above, so Prefect
    # @task decorators don't trigger an API server lookup at module load time.
    log.info("Importing ETL modules…")
    from etl.tasks.crs_helpers import get_engine, load_received_comments  # noqa: PLC0415
    from etl.tasks.crs_text_generalizer import group_by_generalized  # noqa: PLC0415
    from etl.tasks.crs_tier0_prefilter import run_tier0  # noqa: PLC0415
    from etl.tasks.crs_tier1_template_matcher import run_tier1  # noqa: PLC0415
    from etl.tasks.crs_tier2_keyword_classifier import run_tier2  # noqa: PLC0415
    log.info("ETL modules loaded.")

    log.info("Starting CRS debug classifier with args: %s", args)

    engine = get_engine()

    # ── 1. Optional reset ─────────────────────────────────────────────────
    if args.reset:
        if args.revision_all:
            log.error("--reset requires --revision (cannot reset all revisions at once).")
            sys.exit(1)
        _reset_classification(engine, args.revision, log)

    # ── 2. Load comments ──────────────────────────────────────────────────
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

    # ── 3. Deduplicate to unique generalised groups ───────────────────────
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

    # ── 4. Run tiers ──────────────────────────────────────────────────────
    remaining: list[dict[str, Any]] = list(comments)
    classified: list[dict[str, Any]] = []
    run_tier = args.tier.lower()

    if run_tier in ("0", "1", "2", "all"):
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

    if run_tier in ("3", "all"):
        if remaining:
            log.info("── Tier 3: LLM classifier ──  (%d comments remaining)", len(remaining))
            _run_tier3_debug(remaining, engine, args, log)
        else:
            log.info("── Tier 3: skipped (no comments remaining after earlier tiers).")

    # ── 5. Summary ────────────────────────────────────────────────────────
    log.info(
        "%s\nDONE.  %d total input comments → %d classified by Tiers 0-2"
        "  |  %d passed to Tier 3  |  %d not processed (--tier=%s).",
        "=" * 70, len(comments), len(classified), len(remaining), 0, args.tier,
    )


if __name__ == "__main__":
    main()
