"""Shared EIS export pipeline: extract → sanitize → validate → transform → write → audit."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from sqlalchemy.engine import Engine

from tasks.export_transforms import sanitize_dataframe, write_csv
from tasks.export_validation import (
    apply_builtin_fixes,
    load_validation_rules,
    store_validation_results,
)


# ---------------------------------------------------------------------------
# UoM lookup utilities
# ---------------------------------------------------------------------------

def _load_uom_lookup(engine) -> dict[str, str]:
    """
    Load alias_lower → symbol_ascii mapping from ontology_core.uom_alias.

    Safe for incremental migration — returns {} if table doesn't exist yet.

    Args:
        engine: SQLAlchemy engine connected to engineering_core.

    Returns:
        Dictionary mapping alias_lower → symbol_ascii for all active UoM aliases.

    Example:
        >>> lookup = _load_uom_lookup(engine)
        >>> lookup.get('bar(g)', 'bar(g)')
        'bar(g)'
    """
    from sqlalchemy import text

    sql = """
        SELECT a.alias_lower, COALESCE(u.symbol_ascii, u.symbol) AS symbol_ascii
        FROM ontology_core.uom_alias a
        JOIN ontology_core.uom u ON u.id = a.uom_id
        WHERE a.object_status = 'Active' AND u.object_status = 'Active'
    """
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(sql)).fetchall()
        return {r.alias_lower: r.symbol_ascii for r in rows}
    except Exception:
        # Table may not exist yet (migration pending) — return empty lookup
        return {}


# ---------------------------------------------------------------------------
# Public: unified export pipeline
# ---------------------------------------------------------------------------

def run_export_pipeline(
    engine: Engine,
    scope: str,
    extract_fn: Callable[[Engine], pd.DataFrame],
    transform_fn: Callable[[pd.DataFrame], pd.DataFrame],
    output_path: Path,
    report_name: str,
    logger: Any,
    persist_violations: bool = False,
) -> dict[str, int]:
    """
    Run a complete EIS export: extract → sanitize → validate → transform → write → audit.

    Replaces the duplicated orchestration block in export_tag_register.py and
    export_equipment_register.py. Each flow retains its own SQL query, extract
    task, and public flow function; only the inner pipeline is unified here.

    Args:
        engine:             SQLAlchemy engine connected to engineering_core.
        scope:              Validation rule scope — 'tag' or 'equipment'.
        extract_fn:         Callable(engine) → raw DataFrame (a Prefect @task).
        transform_fn:       Callable(df) → clean DataFrame ready for CSV write.
        output_path:        Destination file path including filename.
        report_name:        Human-readable name used in log messages.
        logger:             Prefect get_run_logger() instance.
        persist_violations: If True, store built-in violations in
                            audit_core.validation_result for historical queries.
                            Off by default — zero behaviour change on existing flows.

    Returns:
        dict with keys:
            "exported"   — rows written to CSV
            "violations" — total violations found (including auto-fixed ones)
    """
    run_id = str(uuid.uuid4())
    logger.info(f"[{report_name}] Starting export run {run_id} → {output_path}")

    raw_df = extract_fn(engine)

    # First sanitize pass: strip encoding artefacts before validation to avoid false-positives
    sanitized_df = sanitize_dataframe(raw_df)

    builtin_rules = load_validation_rules(engine, scope=scope, builtin_only=True)
    fixed_df, all_violations = apply_builtin_fixes(
        sanitized_df, builtin_rules, report_name, logger
    )

    clean_df = transform_fn(fixed_df)
    row_count = write_csv(clean_df, output_path)
    logger.info(f"[{report_name}] Exported {row_count} rows to {output_path}")

    if persist_violations and all_violations:
        # Enrich built-in violation records with fields required by validation_result schema
        rule_meta = {r["rule_code"]: r for r in builtin_rules}
        session_id = str(uuid.uuid4())
        run_time = datetime.now()
        enriched = [
            {
                "session_id":       session_id,
                "run_time":         run_time,
                "rule_code":        v["rule_code"],
                "scope":            rule_meta.get(v["rule_code"], {}).get("scope", scope),
                "severity":         rule_meta.get(v["rule_code"], {}).get("severity", "Warning"),
                "object_type":      scope,
                "object_id":        None,
                "object_name":      v.get("object_name"),
                "violation_detail": v.get("detail"),
                "column_name":      v.get("column_name"),
                "original_value":   v.get("original_value"),
                "tier":             rule_meta.get(v["rule_code"], {}).get("tier"),
                "category":         rule_meta.get(v["rule_code"], {}).get("category"),
                "check_type":       rule_meta.get(v["rule_code"], {}).get("check_type", "dsl"),
            }
            for v in all_violations
        ]
        store_validation_results(engine, enriched)
        logger.info(
            f"[{report_name}] Persisted {len(enriched)} violation record(s) "
            f"to audit_core.validation_result (session {session_id})"
        )

    return {"exported": row_count, "violations": len(all_violations)}
