"""Configurable pre-export validation engine for EIS registers.

Two modes:
  - Built-in (apply_builtin_fixes): runs during export generation; auto-fixes
    violations where fix_expression is defined; value in DB is unchanged.
  - Full scan (run_full_scan): runs all rules, stores results in
    audit_core.validation_result; nothing is modified.

DSL — rule_expression (violation condition):
    <col_spec> <op> [<value>]
    <clause1> AND <clause2>

    col_spec: '*' (all object columns) | column name (case-insensitive)
    operators: contains, icontains, max_length, is_null, not_null, matches_regex, equals_col
    equals_col  — compare column to another column by name (cross-column equality)

DSL — fix_expression (auto-fix for built-in mode):
    replace "X" "Y"   — replace all occurrences of X with Y
    replace_nan       — replace literal 'nan'/'NaN' with empty string
    remove_char "X"   — remove all occurrences of X
    truncate N        — truncate string to at most N characters
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    """Raised when a blocking built-in rule has violations and no fix is defined."""


class ExpressionParseError(Exception):
    """Raised when a rule_expression or fix_expression cannot be parsed."""


# ---------------------------------------------------------------------------
# DSL parser — rule_expression
# ---------------------------------------------------------------------------

_QUOTED_VALUE = re.compile(r'"([^"]*)"')


def _parse_expression(expr: str) -> dict[str, Any]:
    """
    Parse a DSL rule_expression string into a structured clause dict.

    Supports:
        <col> <op> [<value>]
        <clause1> AND <clause2>

    Args:
        expr: Raw rule_expression string from DB.

    Returns:
        Clause dict with keys 'type', and type-specific keys.
        type='simple': {col, op, value}
        type='and':    {left: clause_dict, right: clause_dict}

    Raises:
        ExpressionParseError: If syntax is not recognised.
    """
    expr = expr.strip()
    # Split on ' AND ' (case-sensitive, surrounded by spaces)
    and_parts = re.split(r'\s+AND\s+', expr, maxsplit=1)
    if len(and_parts) == 2:
        return {
            "type": "and",
            "left": _parse_expression(and_parts[0]),
            "right": _parse_expression(and_parts[1]),
        }
    # Simple clause: <col> <op> [<value>]
    tokens = expr.split(None, 2)
    if len(tokens) < 2:
        raise ExpressionParseError(f"Cannot parse expression: {expr!r}")
    col = tokens[0]
    op = tokens[1].lower()
    value: str | None = None
    if len(tokens) == 3:
        # Strip surrounding quotes from value token
        m = _QUOTED_VALUE.match(tokens[2].strip())
        value = m.group(1) if m else tokens[2].strip()
    return {"type": "simple", "col": col, "op": op, "value": value}


# ---------------------------------------------------------------------------
# DSL evaluator — violation mask
# ---------------------------------------------------------------------------

def _eval_single_clause(
    df: pd.DataFrame,
    col: str,
    op: str,
    value: str | None,
) -> pd.Series:
    """
    Evaluate one clause. Returns boolean Series — True where violation exists.

    col='*' expands to OR across all object-dtype columns.
    All checks operate on lowercase column names (pd.read_sql returns lowercase).

    Args:
        df:    DataFrame to check.
        col:   Column specifier ('*' or column name, case-insensitive).
        op:    Operator string.
        value: Optional string value for the operator.

    Returns:
        Boolean pd.Series aligned with df.index.
    """
    def _apply_op(series: pd.Series) -> pd.Series:
        s = series.astype(str)
        if op == "contains":
            return s.str.contains(value or "", na=False, regex=False)
        if op == "icontains":
            return s.str.lower().str.contains((value or "").lower(), na=False, regex=False)
        if op == "max_length":
            n = int(value or 0)
            return s.str.len() > n
        if op == "is_null":
            return series.isna() | (s.str.strip() == "") | (s.str.lower() == "none")
        if op == "not_null":
            return ~(series.isna() | (s.str.strip() == "") | (s.str.lower() == "none"))
        if op == "matches_regex":
            # Guard: pandas str.contains() misbehaves with capture groups.
            # Convert (X) → (?:X) so patterns from the DB are always safe.
            pattern = re.sub(r'\((?!\?)', '(?:', value or "")
            # Case-insensitive: DB may store ACTIVE/VOID (uppercase) while rules reference Active/Void
            return s.str.contains(pattern, na=False, regex=True, flags=re.IGNORECASE)
        if op == "has_encoding_artefacts":
            # Detect any known encoding corruption pattern from clean_engineering_text pipeline
            _ENCODING_PATTERNS = (
                "\u00c2\u00b2", "\u00c2\u00b0", "\u00c2\u00b3",   # Â² Â° Â³
                "\u00e2\u0080\u009c", "\u00e2\u0080\u009d",         # â€œ â€
                "\u00e2\u0080\u0099", "\u00e2\u0080\u0093",         # â€™ â€"
                "\u00c2\xa0", "\u00c2", "\u00e2",                   # NBSP, orphan leading bytes
                "\x93", "\x9d",                                     # Win-1252 raw quote bytes
            )
            return series.fillna("").astype(str).apply(
                lambda v: any(p in v for p in _ENCODING_PATTERNS)
            )
        if op == "equals_col":
            target_lower = (value or "").lower()
            target_matched = [c for c in df.columns if c.lower() == target_lower]
            if not target_matched:
                return pd.Series(False, index=df.index)
            other = df[target_matched[0]].astype(str)
            return (
                series.notna()
                & df[target_matched[0]].notna()
                & (series.astype(str) == other)
            )
        raise ExpressionParseError(f"Unknown operator: {op!r}")

    base_mask = pd.Series(False, index=df.index)

    if col == "*":
        # Apply to all object (string) columns; combine with OR
        for c in df.select_dtypes(include="object").columns:
            base_mask = base_mask | _apply_op(df[c])
        return base_mask

    # Specific column — case-insensitive lookup
    col_lower = col.lower()
    matched = [c for c in df.columns if c.lower() == col_lower]
    if not matched:
        # Column absent in this DataFrame — rule does not apply, no violations
        return base_mask
    return _apply_op(df[matched[0]])


def _eval_expression(df: pd.DataFrame, clause: dict[str, Any]) -> pd.Series:
    """
    Recursively evaluate a parsed clause dict against df.

    AND = logical AND of left and right masks (both conditions on same row).

    Args:
        df:     DataFrame to evaluate.
        clause: Parsed clause dict from _parse_expression().

    Returns:
        Boolean pd.Series — True where violation.
    """
    if clause["type"] == "and":
        return _eval_expression(df, clause["left"]) & _eval_expression(df, clause["right"])
    # Simple clause
    return _eval_single_clause(df, clause["col"], clause["op"], clause["value"])


# ---------------------------------------------------------------------------
# DSL interpreter — fix_expression
# ---------------------------------------------------------------------------

def _apply_fix(df: pd.DataFrame, col_spec: str, fix_expr: str) -> pd.DataFrame:
    """
    Apply a fix_expression to df columns matching col_spec.

    Mutates df in-place. Caller is responsible for passing a copy if immutability
    of the original is required (apply_builtin_fixes owns this invariant).

    Supported fix_expression syntax:
        replace "X" "Y"   — replace substring X with Y in target columns
        replace_nan       — replace literal 'nan'/'NaN' strings with ''
        remove_char "X"   — remove all occurrences of X
        truncate N        — truncate string to at most N characters

    Args:
        df:        DataFrame to fix (mutated in-place).
        col_spec:  '*' or specific column name (case-insensitive).
        fix_expr:  Fix expression string.

    Returns:
        The same df object after applying the fix.
    """
    fix_expr = fix_expr.strip()

    # Determine target columns
    if col_spec == "*":
        target_cols = list(df.select_dtypes(include="object").columns)
    else:
        col_lower = col_spec.lower()
        target_cols = [c for c in df.columns if c.lower() == col_lower]

    def _fix_series(s: pd.Series) -> pd.Series:
        # encoding_repair — delegate to clean_engineering_text() (idempotent)
        if fix_expr == "encoding_repair":
            from tasks.export_transforms import clean_engineering_text
            return s.apply(lambda v: clean_engineering_text(v) if isinstance(v, str) else v)
        # replace "X" "Y"
        m = re.fullmatch(r'replace\s+"([^"]*)"\s+"([^"]*)"', fix_expr)
        if m:
            return s.astype(str).str.replace(m.group(1), m.group(2), regex=False)
        # replace_nan
        if fix_expr == "replace_nan":
            return s.astype(str).str.replace(r"^(?i:nan)$", "", regex=True)
        # remove_char "X"
        m = re.fullmatch(r'remove_char\s+"([^"]*)"', fix_expr)
        if m:
            return s.astype(str).str.replace(m.group(1), "", regex=False)
        # truncate N
        m = re.fullmatch(r'truncate\s+(\d+)', fix_expr)
        if m:
            n = int(m.group(1))
            return s.astype(str).str[:n]
        # normalize_na — replace all NA-variant strings with strict "NA"
        # (Power Query equivalent: N/A → NA, N.A. → NA, na → NA)
        if fix_expr == "normalize_na":
            return s.astype(str).str.replace(r"(?i)^(N\.A\.?|N/A|na|n/a)$", "NA", regex=True)
        # normalize_boolean_case — Title-case EIS boolean picklist values
        # (Power Query: YES → Yes, NO → No — ALL CAPS rejected by EIS picklist validator)
        if fix_expr == "normalize_boolean_case":
            return s.replace({"YES": "Yes", "NO": "No"})
        # normalize_uom_longform — replace SI unit long-forms with abbreviations
        # (Power Query UoM normalization: ampere→A, volt→V, pascal→Pa, hertz→Hz, kilowatt→kW)
        if fix_expr == "normalize_uom_longform":
            _UOM_MAP = {
                "ampere": "A", "volt": "V", "pascal": "Pa",
                "hertz": "Hz", "kilowatt": "kW",
            }
            _pattern = "|".join(re.escape(k) for k in _UOM_MAP)
            return s.astype(str).str.replace(
                r"(?i)\b(" + _pattern + r")\b",
                lambda m_: _UOM_MAP.get(m_.group(0).lower(), m_.group(0)),
                regex=True,
            )
        # normalize_pseudo_null — replace entire value with "NA" for all pseudo-null placeholders:
        # numeric (9{5,} + optional unit suffix), ALL prefix variants with - or _ (Tag-NA, Signal_NA),
        # verbose variants (N.A., n/a, not applicable), epoch date placeholder (01/01/1990), single dash.
        # Each matched value is replaced wholesale — non-matching values are left unchanged.
        if fix_expr == "normalize_pseudo_null":
            _NULL_RE = re.compile(
                r"^9{5,}[\d./a-zA-Z ]*$"    # numeric: 9{5,} + optional unit/digit suffix
                r"|^[A-Za-z]+[-_]NA$"        # ALL prefix variants with - or _ (Tag-NA, Signal_NA, etc.)
                r"|^01/01/1990"              # epoch date placeholder (source default "no date")
                r"|^-$"                      # single dash pseudo-null
                r"|(?i)^(N\.A\.|n/a|n\.a\.|not\s+applicable|not\s+appl\.?)$"  # verbose variants
            )
            return s.astype(str).apply(lambda v: "NA" if _NULL_RE.match(v) else v)
        # strip_edge_char "X" — remove leading/trailing occurrences of char X
        # DB-driven equivalent of Python s.strip("X").strip()
        # Example fix_expression: strip_edge_char "-"
        m = re.fullmatch(r'strip_edge_char\s+"([^"]*)"', fix_expr)
        if m:
            char = m.group(1)
            return s.astype(str).str.strip(char).str.strip()
        # split_value_uom — handled at DataFrame level, not series level
        # This fix_expression is a marker; actual splitting happens in transform functions
        if fix_expr == "split_value_uom":
            return s  # No-op: splitting handled in transform_tag/equipment_properties
        raise ExpressionParseError(f"Unknown fix_expression: {fix_expr!r}")

    for col in target_cols:
        df[col] = _fix_series(df[col])

    return df


# ---------------------------------------------------------------------------
# Public: load rules from DB
# ---------------------------------------------------------------------------

def load_validation_rules(
    engine: Engine,
    scope: str,
    builtin_only: bool = False,
) -> list[dict[str, Any]]:
    """
    Load active validation rules for the given scope plus all 'common' rules.

    Args:
        engine:       SQLAlchemy engine connected to engineering_core.
        scope:        Report scope — 'tag' or 'equipment'.
        builtin_only: If True, load only rules where is_builtin = true.

    Returns:
        List of rule dicts with keys matching export_validation_rule columns.
    """
    builtin_clause = "AND is_builtin = true" if builtin_only else ""
    sql = text(f"""
        SELECT rule_code, scope, object_field, description,
               rule_expression, fix_expression, is_builtin, is_blocking, severity,
               tier, category, check_type, source_ref
        FROM audit_core.export_validation_rule
        WHERE object_status = 'Active'
          AND scope IN ('common', :scope)
          AND COALESCE(check_type, 'dsl') = 'dsl'
          {builtin_clause}
        ORDER BY tier NULLS LAST, scope, rule_code
    """)
    # SELECT-only: engine.connect() is sufficient
    with engine.connect() as conn:
        rows = conn.execute(sql, {"scope": scope}).fetchall()
    rules = [dict(r._mapping) for r in rows]
    if not rules:
        import logging
        logging.getLogger(__name__).warning(
            "No DSL validation rules found for scope=%r. "
            "Export will proceed without built-in validation. "
            "Seed rules in audit_core.export_validation_rule to enable.",
            scope,
        )
    return rules


# ---------------------------------------------------------------------------
# Public: built-in mode — apply fixes during export
# ---------------------------------------------------------------------------

def apply_builtin_fixes(
    df: pd.DataFrame,
    rules: list[dict[str, Any]],
    report_name: str,
    logger: Any,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """
    Apply built-in auto-fixes to df for all provided rules.

    For each rule:
    - Evaluate violation mask via DSL interpreter.
    - If violations found AND fix_expression is set: apply fix to df copy (INFO logged).
    - If violations found AND no fix_expression AND is_blocking: log ERROR (field will be
      empty in report — data impact), export continues.
    - If violations found AND no fix_expression AND not blocking: log WARNING.

    Export is never aborted. Value in DB is never modified — only the returned DataFrame
    is changed. count_errors in the audit record reflects total violation count.

    Args:
        df:          DataFrame extracted from DB (sanitized, pre-transform).
        rules:       Rule dicts from load_validation_rules(builtin_only=True).
        report_name: Human-readable report name for log messages.
        logger:      Prefect get_run_logger() instance.

    Returns:
        Tuple of (fixed_df, all_violations).
        fixed_df has auto-fixes applied; all_violations lists every violation found.
    """
    # Guard: scope='sync' rules carry plain-English rule_expression not parseable by DSL
    rules = [r for r in rules if r.get("scope") != "sync"]

    fixed_df = df.copy()
    all_violations: list[dict[str, Any]] = []

    for rule in rules:
        rule_code = rule["rule_code"]
        fix_expr = rule.get("fix_expression")
        is_blocking = rule.get("is_blocking", False)

        try:
            clause = _parse_expression(rule["rule_expression"])
            mask = _eval_expression(fixed_df, clause)
        except ExpressionParseError as exc:
            logger.error(f"[{report_name}] Cannot parse rule {rule_code!r}: {exc}")
            continue

        violating_rows = fixed_df[mask]
        if violating_rows.empty:
            continue

        # Determine target column for enriched violation records
        col_spec = clause.get("col", "*") if clause["type"] == "simple" else "*"

        # Resolve identity columns once per rule (case-insensitive, nullable)
        _tag_col = next((c for c in fixed_df.columns if c.upper() == "TAG_NAME"), None)
        _equip_col = next((c for c in fixed_df.columns if c.upper() == "EQUIPMENT_NUMBER"), None)

        # Collect violation details with row identity for observability
        row_violations = [
            {
                "rule_code":      rule_code,
                "row_index":      idx,
                "object_name":    str(
                    (fixed_df.at[idx, _tag_col] if _tag_col else None)
                    or (fixed_df.at[idx, _equip_col] if _equip_col else None)
                    or idx
                ),
                "column_name":    col_spec if col_spec != "*" else None,
                "original_value": (
                    str(fixed_df.at[idx, col_spec])[:200]
                    if col_spec != "*" and col_spec in fixed_df.columns
                    else None
                ),
                "detail":         f"Rule {rule_code!r} violated at row {idx}",
            }
            for idx in violating_rows.index
        ]
        all_violations.extend(row_violations)

        if fix_expr:
            # AND-clause fix applies to all string columns — warn if this is unexpected
            if clause["type"] == "and":
                logger.warning(
                    f"[{report_name}] Rule {rule_code!r}: AND-clause with fix_expression — "
                    f"fix will be applied to ALL string columns. Verify this is intentional."
                )
            _apply_fix(fixed_df, col_spec, fix_expr)
            logger.info(
                f"[{report_name}] Rule {rule_code!r}: auto-fixed {len(row_violations)} "
                f"violation(s) using fix_expression={fix_expr!r}"
            )
        elif is_blocking:
            # Field-level impact: field will be empty in report — log as error, export continues
            logger.error(
                f"[{report_name}] Rule {rule_code!r}: "
                f"{len(row_violations)} violation(s) — field will be empty in report"
            )
        else:
            logger.warning(
                f"[{report_name}] Rule {rule_code!r}: "
                f"{len(row_violations)} violation(s) — non-blocking, continuing"
            )

    return fixed_df, all_violations


# ---------------------------------------------------------------------------
# Public: full scan mode — collect all violations, store to DB
# ---------------------------------------------------------------------------

def run_full_scan(
    df: pd.DataFrame,
    rules: list[dict[str, Any]],
    session_id: str,
    object_type: str,
    id_col: str | None,
    name_col: str | None,
    logger: Any,
) -> list[dict[str, Any]]:
    """
    Evaluate all rules against df. Collects violations without modifying anything.

    Args:
        df:          DataFrame to scan.
        rules:       All active rules for the target scope.
        session_id:  UUID string grouping this scan session.
        object_type: Domain type of the scanned object (e.g. 'tag', 'document').
        id_col:      Column name in df containing the record UUID (nullable).
        name_col:    Column name in df containing the human-readable name (nullable).
        logger:      Prefect get_run_logger() or standard logger.

    Returns:
        List of violation dicts ready for store_validation_results().
    """
    # Guard: scope='sync' rules carry plain-English rule_expression not parseable by DSL
    rules = [r for r in rules if r.get("scope") != "sync"]

    results: list[dict[str, Any]] = []
    run_time = datetime.now()

    for rule in rules:
        rule_code = rule["rule_code"]
        severity = rule.get("severity", "Warning")
        scope = rule.get("scope", "common")
        tier = rule.get("tier")
        category = rule.get("category")
        check_type = rule.get("check_type", "dsl")

        try:
            clause = _parse_expression(rule["rule_expression"])
            mask = _eval_expression(df, clause)
        except ExpressionParseError as exc:
            logger.error(f"[full_scan] Cannot parse rule {rule_code!r}: {exc}")
            continue

        violating_rows = df[mask]
        if violating_rows.empty:
            continue

        logger.warning(
            f"[full_scan] Rule {rule_code!r} ({severity}): "
            f"{len(violating_rows)} violation(s)"
        )

        for idx, vrow in violating_rows.iterrows():
            object_id_val = str(vrow[id_col]) if id_col and id_col in df.columns else None
            object_name_val = str(vrow[name_col]) if name_col and name_col in df.columns else None

            # Determine which column triggered the violation for simple single-col rules
            col_name: str | None = None
            original_val: str | None = None
            if clause["type"] == "simple" and clause["col"] != "*":
                col_lower = clause["col"].lower()
                matched = [c for c in df.columns if c.lower() == col_lower]
                if matched:
                    col_name = matched[0]
                    original_val = str(vrow[matched[0]])

            results.append({
                "session_id": session_id,
                "run_time": run_time,
                "rule_code": rule_code,
                "scope": scope,
                "severity": severity,
                "object_type": object_type,
                "object_id": object_id_val,
                "object_name": object_name_val,
                "violation_detail": (
                    f"Rule {rule_code!r} violated"
                    + (f" in column {col_name!r}: {original_val!r}" if col_name else "")
                ),
                "column_name": col_name,
                "original_value": original_val,
                "tier": tier,
                "category": category,
                "check_type": check_type,
            })

    return results


# ---------------------------------------------------------------------------
# Public: persist full scan results
# ---------------------------------------------------------------------------

def store_validation_results(engine: Engine, results: list[dict[str, Any]]) -> None:
    """
    Bulk INSERT validation results into audit_core.validation_result.

    Args:
        engine:  SQLAlchemy engine.
        results: Violation dicts from run_full_scan() or manual TAG_NAME_CHANGED detection.
    """
    if not results:
        return
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO audit_core.validation_result
                    (session_id, run_time, rule_code, scope, severity, object_type,
                     object_id, object_name, violation_detail, column_name, original_value,
                     tier, category, check_type)
                VALUES
                    (:session_id, :run_time, :rule_code, :scope, :severity, :object_type,
                     :object_id::uuid, :object_name, :violation_detail, :column_name, :original_value,
                     :tier, :category, :check_type)
            """),
            results,
        )
