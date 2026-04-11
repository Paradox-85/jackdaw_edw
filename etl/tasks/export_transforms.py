"""Shared utilities for all Reverse ETL export flows."""

import re as _re
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Value / UoM split — regex patterns (_P1–_P4)
# ---------------------------------------------------------------------------
# These patterns handle STRUCTURAL splitting only — where to cut value from UoM.
# They do NOT map raw UoM tokens to canonical form; that is the job of
# _resolve_uom_symbol() which looks up ontology_core.uom_alias via uom_lookup.
#
# Why Python regexes instead of DB rules:
#   The DSL validation engine (export_validation.py) operates on one pd.Series
#   at a time and cannot write to two columns simultaneously. Splitting
#   "490mm" → PROPERTY_VALUE="490" + PROPERTY_VALUE_UOM="mm" requires exactly
#   that. VALUE_UOM_COMBINED_IN_CELL in audit_core.export_validation_rule
#   (fix_expression='split_value_uom') therefore acts as a DETECTOR only.
#   These patterns do the actual work.
#
# Pattern priority (evaluated top-to-bottom, first match wins):
# P1: Inch — numeric or fractional (e.g. "1 1/2\"") followed by double-quote
#     value="1 1/2",  uom="inch"   (hardcoded — no alias lookup needed)
# P2: Degree-letter — numeric ending with °, optional space then letter(s)
#     "+60°C"  → value="+60",       uom="degC"   (via uom_lookup)
#     "+60°"   → value="+60",       uom="degC"   (bare ° defaults to degC)
# P3: Percent + qualifier
#     "0% LEL" → value="0",         uom="% LEL"  (via uom_lookup)
#     "100%"   → value="100",        uom="%"
# P4: Standard numeric + UoM token (with or without space)
#     "490mm"           → value="490",      uom="mm"
#     "4 - 50 mm"       → value="4 - 50",   uom="mm"
#     "-50 - 450 Deg C" → value="-50 - 450", uom="degC"  (via uom_lookup)

# P1: inch — standalone number (incl. fractions like "1 1/2") then double-quote
_P1_INCH_RE = _re.compile(
    r'^(?P<value>[+-]?[\d.,/ ]+(?:\s*[-–]\s*[+-]?[\d.,/ ]+)?)\s*"$'
)

# P2: degree-letter — number then ° then optional space then letters
_P2_DEG_RE = _re.compile(
    r"^(?P<value>[+-]?[\d.,]+(?:\s*[-–]\s*[+-]?[\d.,]+)?)\s*°\s*(?P<letter>[A-Za-z]*)$"
)

# P3: percent — number then % then optional qualifier
_P3_PCT_RE = _re.compile(
    r"^(?P<value>[+-]?[\d.,]+(?:\s*[-–]\s*[+-]?[\d.,]+)?)\s*(?P<uom>%[A-Za-z0-9°²³/.*()\s\-]*)$"
)

# P4: standard — number (with optional sign/range) then space then UoM token
# UoM token may contain spaces (e.g. "Deg C") — capture remainder of string
_P4_STD_RE = _re.compile(
    r"^(?P<value>[+-]?[\d.,]+(?:\s*[-–]\s*[+-]?[\d.,]+)?)\s+"
    r"(?P<uom>[A-Za-z°²³µμ%][A-Za-z0-9°²³/.*()\s\-]*)$"
    r"|"
    # no-space variant: number immediately followed by UoM (no spaces)
    r"^(?P<value2>[+-]?[\d.,]+(?:\s*[-–]\s*[+-]?[\d.,]+)?)"
    r"(?P<uom2>[A-Za-z°²³µμ%][A-Za-z0-9°²³/.*()\-]*)$"
)


def _resolve_uom_symbol(raw_uom: str, uom_lookup: dict[str, str]) -> str:
    """
    Resolve raw UoM to canonical symbol_ascii via alias_lookup.

    Args:
        raw_uom: Raw UoM string from source data.
        uom_lookup: Dictionary mapping alias_lower → symbol_ascii.

    Returns:
        Canonical symbol_ascii if found in lookup, otherwise stripped raw_uom.

    Example:
        >>> lookup = {'bar(g)': 'bar(g)', 'mm2': 'mm2'}
        >>> _resolve_uom_symbol('BAR(G)', lookup)
        'bar(g)'
    """
    if not raw_uom:
        return ""
    return uom_lookup.get(raw_uom.strip().lower(), raw_uom.strip())


def _split_value_uom(
    value: str, uom: str, uom_lookup: dict[str, str]
) -> tuple[str, str]:
    """
    Split combined value and UoM token into separate fields.

    Handles the following source data patterns found in engineering datasets:

    Standard numeric+UoM (no-space):
        "490mm"        → ("490",    "mm")
        "100kW"        → ("100",    "kW")
        "49063mm2"     → ("49063",  "mm2")

    Standard numeric+UoM (with space):
        "4 - 50 mm"    → ("4 - 50", "mm")
        "3.5 bar(g)"   → ("3.5",    "bar(g)")
        "25 degC"      → ("25",     "degC")

    Range notation with multi-word UoM:
        "-50 - 450 Deg C" → ("-50 - 450", "Deg C")   # resolved to degC via alias

    Signed values:
        "+60° C"       → ("+60",    "degC")    # ° stripped, "C" merged to "deg"
        "-60°"         → ("-60",    "degC")    # bare degree → canonical degC

    Inch notation (double-quote):
        "6\""          → ("6",      "inch")    # hardcoded; no alias needed
        "1 1/2\""      → ("1 1/2",  "inch")    # fractional inch

    Percent with qualifier:
        "0% LEL"       → ("0",      "% LEL")
        "100%"         → ("100",    "%")

    No-op cases — returned unchanged:
        uom already set:  ("490", "mm", ...)   → ("490", "mm")
        pure text:        ("Active", "", ...)  → ("Active", "")
        pseudo-null:      ("NA", "", ...)      → ("NA", "")
        already split:    ("100", "kW", ...)   → ("100", "kW")

    UoM case normalization:
        All extracted UoM tokens are passed through _resolve_uom_symbol().
        If the token is found in uom_lookup (alias_lower → symbol_ascii),
        the canonical symbol_ascii is returned.
        If not found, the raw token is returned stripped but case-preserved.
        Callers must NOT uppercase the UoM column globally — canonical symbols
        may be mixed-case (e.g. "kPa(g)", "degC", "mbar").

    Args:
        value: Property value string, potentially with embedded UoM.
        uom: Separate UoM column value. If non-empty, function is a no-op.
        uom_lookup: Dict mapping lower(alias) → symbol_ascii.

    Returns:
        Tuple (clean_value, canonical_uom).

    Examples:
        >>> lookup = {'mm': 'mm', 'bar(g)': 'bar(g)', 'deg c': 'degC'}
        >>> _split_value_uom('490mm', '', lookup)
        ('490', 'mm')
        >>> _split_value_uom('0% LEL', '', lookup)
        ('0', '% LEL')
        >>> _split_value_uom('+60° C', '', lookup)
        ('+60', 'degC')
        >>> _split_value_uom('-50 - 450 Deg C', '', lookup)
        ('-50 - 450', 'degC')
        >>> _split_value_uom('6\"', '', lookup)
        ('6', 'inch')
        >>> _split_value_uom('490', 'mm', lookup)
        ('490', 'mm')
        >>> _split_value_uom('Active', '', lookup)
        ('Active', '')
    """
    if uom.strip():
        # UoM already provided separately — no-op
        return value, uom
    if not isinstance(value, str) or not value.strip():
        return value, uom

    s = value.strip()

    # P1: Inch — "6\"" → ("6", "inch")
    m = _P1_INCH_RE.match(s)
    if m:
        return m.group("value").strip(), "inch"

    # P2: Degree-letter — "-60°C", "+60° C", "-60°"
    # ° is consumed; letter part (if any) merged with "deg" prefix
    m = _P2_DEG_RE.match(s)
    if m:
        letter = (m.group("letter") or "").strip()
        raw_uom = "deg" + letter if letter else "degC"  # bare ° defaults to degC
        canon_uom = _resolve_uom_symbol(raw_uom, uom_lookup)
        return m.group("value").strip(), canon_uom

    # P3: Percent — "0% LEL" → ("0", "% LEL"), "100%" → ("100", "%")
    m = _P3_PCT_RE.match(s)
    if m:
        raw_uom = m.group("uom").strip()
        canon_uom = _resolve_uom_symbol(raw_uom, uom_lookup)
        return m.group("value").strip(), canon_uom

    # P4: Standard — space-separated or no-space variants
    m = _P4_STD_RE.match(s)
    if m:
        if m.group("value") is not None:
            clean_val = m.group("value").strip()
            raw_uom = m.group("uom").strip()
        else:
            clean_val = m.group("value2").strip()
            raw_uom = m.group("uom2").strip()
        canon_uom = _resolve_uom_symbol(raw_uom, uom_lookup)
        return clean_val, canon_uom

    return value, uom


def _apply_value_uom_split(
    df: pd.DataFrame,
    value_col: str = "PROPERTY_VALUE",
    uom_col: str = "PROPERTY_VALUE_UOM",
    uom_lookup: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Apply _split_value_uom row-wise to a DataFrame.

    Args:
        df: DataFrame containing property value columns.
        value_col: Name of the column containing values (may include embedded UoM).
        uom_col: Name of the UoM column (will be updated if empty).
        uom_lookup: Dict alias_lower → symbol_ascii loaded from ontology_core.uom_alias
                    via _load_uom_lookup(engine). Populated once per flow run.
                    If None or empty, split still occurs but UoM tokens are returned
                    as-is (no canonicalization). Raw token is NOT uppercased — canonical
                    symbols are mixed-case (e.g. "kPa(g)", "degC", "mbar").

    Returns:
        DataFrame with split and normalized value/UoM columns.

    Example:
        >>> df = pd.DataFrame({'PROPERTY_VALUE': ['490mm', '3.5bar(g)', 'NA'], 'PROPERTY_VALUE_UOM': ['', '', '']})
        >>> lookup = {'mm': 'mm', 'bar(g)': 'bar(g)'}
        >>> result = _apply_value_uom_split(df, uom_lookup=lookup)
        >>> result['PROPERTY_VALUE'].tolist()
        ['490', '3.5', 'NA']
        >>> result['PROPERTY_VALUE_UOM'].tolist()
        ['mm', 'bar(g)', '']
    """
    if uom_lookup is None:
        uom_lookup = {}
    if value_col not in df.columns or uom_col not in df.columns:
        return df

    result = df.apply(
        lambda r: pd.Series(
            _split_value_uom(
                str(r[value_col]) if pd.notna(r[value_col]) else "",
                str(r[uom_col]) if pd.notna(r[uom_col]) else "",
                uom_lookup,
            ),
            index=[value_col, uom_col],
        ),
        axis=1,
    )
    df = df.copy()
    df[[value_col, uom_col]] = result
    return df


# ---------------------------------------------------------------------------
# Pseudo-null normalization
# ---------------------------------------------------------------------------

# Ordered list of (compiled_regex, replacement) pairs.
# Evaluated top-to-bottom; first match wins.
_PSEUDO_NULL_PATTERNS: list[tuple[_re.Pattern, str]] = [
    # Already canonical — fast-path no-op
    (_re.compile(r"^NA$"), "NA"),
    # Large sentinel numbers: 999999, 9999999, etc. (5+ nines)
    (_re.compile(r"^9{5,}$"), "NA"),
    # Epoch date placeholders: 01/01/1990, 01.01.1990
    (_re.compile(r"^01[./]01[./]1990$"), "NA"),
    # Bare dash (common "no value" placeholder in legacy data)
    (_re.compile(r"^-$"), "NA"),
    # Domain/tag-prefixed NA variants:
    #   Dash separator:       Area-NA, PU-NA, PO-NA, Tag-NA, Loop-NA
    #   Underscore separator: Area_NA, PU_NA, PO_NA, Tag_NA, Loop_NA
    #   Covers all prefix families per DOMAIN_PREFIX_NA + TAG_PREFIX_NA rules.
    (_re.compile(r"^[A-Za-z]+[-_]NA$"), "NA"),
    # Verbose "not applicable" variants (case-insensitive):
    #   N.A., n/a, n.a., not applicable, not appl., N/A
    #   Canonical target: "NA" (no dots, no slashes, exact uppercase)
    (_re.compile(r"(?i)^(N\.A\.|n/a|n\.a\.|not\s+applicable|not\s+appl\.?)$"), "NA"),
]


def normalize_pseudo_null(value: str) -> str:
    """
    Normalize pseudo-null sentinel values to the canonical string "NA".

    Source data contains many encodings of "no value" — this function
    collapses all known variants to the single canonical sentinel "NA"
    so that downstream validation rules (DOMAIN_PREFIX_NA, TAG_PREFIX_NA,
    NOT_APPLICABLE_VARIANT) have a consistent target to check.

    Handled patterns:
    - Already canonical:     "NA"              → "NA"   (fast-path)
    - Large sentinel nums:   "999999"          → "NA"
    - Epoch date:            "01/01/1990"      → "NA"
    - Bare dash:             "-"               → "NA"
    - Prefixed (dash):       "Area-NA", "PU-NA", "Tag-NA"   → "NA"
    - Prefixed (underscore): "Area_NA", "PU_NA", "Tag_NA"   → "NA"
    - Verbose variants:      "N.A.", "n/a", "not applicable" → "NA"

    Negative cases (must NOT be normalized):
    - "PU_NAP"   — contains NA but not suffix  → unchanged
    - "BANANA"   — contains NA but not suffix  → unchanged
    - "TBC"      — valid export placeholder    → unchanged

    Args:
        value: Input string. Non-string values are returned unchanged.

    Returns:
        "NA" if value matches a pseudo-null pattern, otherwise the original value.

    Examples:
        >>> normalize_pseudo_null('PU_NA')
        'NA'
        >>> normalize_pseudo_null('not applicable')
        'NA'
        >>> normalize_pseudo_null('BANANA')
        'BANANA'
        >>> normalize_pseudo_null('PU_NAP')
        'PU_NAP'
    """
    if not isinstance(value, str):
        return value
    for pattern, replacement in _PSEUDO_NULL_PATTERNS:
        if pattern.match(value):
            return replacement
    return value


# ---------------------------------------------------------------------------
# Encoding sanitizer
# ---------------------------------------------------------------------------

def clean_engineering_text(value: str) -> str:
    """
    Repair encoding corruption common in engineering tag descriptions.

    Applies a 12-step pipeline targeting UTF-8 mojibake and Win-1252
    byte leakage found in 1927 TAG_DESCRIPTION source rows.

    Args:
        value: Raw string potentially containing encoding artefacts.

    Returns:
        Cleaned string with collapsed whitespace and stripped edges.

    Example:
        >>> clean_engineering_text("Pressure Â² sensor")
        'Pressure 2 sensor'
    """
    if not value or not isinstance(value, str):
        return value

    s = value

    # Steps 1-3: UTF-8 superscript mojibake pairs (Â + combining char)
    s = s.replace("\u00c2\u00b2", "2")   # Â² → 2
    s = s.replace("\u00c2\u00b0", "°")   # Â° → degree sign
    s = s.replace("\u00c2\u00b3", "3")   # Â³ → 3

    # Steps 4-6: Win-1252 smart quotes / dashes leaked as 3-byte UTF-8
    s = s.replace("\u00e2\u0080\u009c", '"')  # â€œ → "
    s = s.replace("\u00e2\u0080\u009d", '"')  # â€  → "
    s = s.replace("\u00e2\u0080\u0099", "'")  # â€™ → '
    s = s.replace("\u00e2\u0080\u0093", "-")  # â€" → en-dash

    # Step 7: NBSP mojibake (Â\xA0 → space)
    s = s.replace("\u00c2\xa0", " ")

    # Step 8: Orphan Â (U+00C2) — leading byte without valid pair
    s = s.replace("\u00c2", "")

    # Step 9: Orphan â (U+00E2) — leading byte without valid pair
    s = s.replace("\u00e2", "")

    # Step 10: Win-1252 smart quotes as raw bytes (survived as latin-1 chars)
    s = s.replace("\x93", '"').replace("\x9d", '"')

    # Step 10b: Unicode hyphens and dashes → ASCII hyphen
    # Power Query: Text.Replace([TAG_NAME], "‐", "-") — affects TAG_NAME and DOCUMENT_NUMBER matching
    s = s.replace("\u2010", "-")   # Unicode hyphen (U+2010)
    s = s.replace("\u2013", "-")   # En-dash (U+2013)
    s = s.replace("\u2014", "-")   # Em-dash (U+2014)

    # Step 10c: Engineering unit superscript artefacts → ASCII equivalents
    # Power Query: Text.Replace([TAG_DESCRIPTION], "MM²", "mm2") — Aveva format requirement
    s = s.replace("MM\u00b2", "mm2")  # MM² → mm2
    s = s.replace("mm\u00b2", "mm2")  # mm² → mm2 (lowercase variant)

    # Step 11: Collapse multiple spaces to single
    s = _re.sub(r" {2,}", " ", s)

    # Step 12: Strip leading/trailing whitespace
    s = s.strip()

    return s


# ---------------------------------------------------------------------------
# DataFrame-level sanitizer
# ---------------------------------------------------------------------------

def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply clean_engineering_text() to every string column in the DataFrame.

    Skips float, int, and datetime columns. Compatible with both pandas 2.x
    StringDtype and classic object dtype.

    Args:
        df: Input DataFrame (modified in-place, copy returned).

    Returns:
        DataFrame with all string columns sanitized.

    Example:
        >>> df = pd.DataFrame({"TAG": ["Â²sensor"], "VAL": [1.0]})
        >>> sanitize_dataframe(df)["TAG"].iloc[0]
        '2sensor'
    """
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].apply(
                lambda x: clean_engineering_text(x) if isinstance(x, str)
                          else ("" if pd.isna(x) else x)
            )
    return df


# ---------------------------------------------------------------------------
# CSV writer — sanitize gate is unconditional
# ---------------------------------------------------------------------------

def write_csv(df: pd.DataFrame, path: Path) -> int:
    """
    Write DataFrame to UTF-8 BOM CSV for EIS/Excel compatibility.

    Calls sanitize_dataframe() unconditionally — no export can bypass
    the encoding sanitizer. Creates parent directories if needed.

    Args:
        df: DataFrame to export.
        path: Destination file path (Path or str).

    Returns:
        Number of rows written (excludes header).

    Example:
        >>> count = write_csv(df, Path("/export/EIS/tags.CSV"))
        >>> count
        1500
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Second sanitize pass — mandatory safety net. Cannot be removed.
    # First pass (in flow, before validation) eliminates encoding false-positives.
    # This pass guarantees no artefacts survive transform_*() column renames and row filters.
    clean_df = sanitize_dataframe(df)
    clean_df.to_csv(path, index=False, encoding="utf-8-sig")
    return len(clean_df)


# ---------------------------------------------------------------------------
# Shared EIS transform logic
# ---------------------------------------------------------------------------

def _apply_common_eis_transforms(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the subset of EIS transforms shared by all register exports.

    Steps performed (in order):
    1. Normalise column names to UPPER_CASE (PostgreSQL returns lowercase aliases).
    2. Second-level defence: retain only object_status = 'Active' rows.
    3. Compute ACTION_STATUS: Void tag_status → 'Deleted', otherwise SYNC_STATUS.
    4. Compute ACTION_DATE from SYNC_TIMESTAMP (DD.MM.YYYY).
    5. Drop internal columns: OBJECT_STATUS, SYNC_STATUS, SYNC_TIMESTAMP.

    Register-specific filtering and column reordering are the caller's responsibility.

    Args:
        df: Raw DataFrame with columns as returned by the SQL extract query.

    Returns:
        New DataFrame with common EIS columns applied.
    """
    df = df.copy()
    df.columns = df.columns.str.upper()

    # Second-level defence: only Active records exported
    df = df[df["OBJECT_STATUS"] == "Active"]

    # Normalise pseudo-null values in FK code fields for correct FK validation
    _CODE_FIELDS = [
        "PROCESS_UNIT_CODE", "AREA_CODE", "PLANT_CODE",
        "TAG_CLASS_NAME", "DESIGNED_BY_COMPANY_NAME",
    ]
    for col in _CODE_FIELDS:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda v: "" if isinstance(v, str) and v.strip().upper() in ("NA", "N/A", "N.A.") else v
            )

    # ACTION_STATUS: Void tag_status always maps to Deleted regardless of sync_status
    # Case-insensitive check — DB may store 'Void', 'VOID', or 'void' depending on source
    df["ACTION_STATUS"] = df.apply(
        lambda row: "Deleted" if str(row.get("TAG_STATUS") or "").upper() == "VOID"
                    else row.get("SYNC_STATUS", ""),
        axis=1,
    )

    # Convert timestamp to date-only string for EIS format
    df["ACTION_DATE"] = pd.to_datetime(df["SYNC_TIMESTAMP"], errors="coerce").dt.strftime("%d.%m.%Y")

    return df.drop(columns=["OBJECT_STATUS", "SYNC_STATUS", "SYNC_TIMESTAMP"], errors="ignore")


# ---------------------------------------------------------------------------
# Tag Register domain transform (seq 003)
# ---------------------------------------------------------------------------

_TAG_REGISTER_COLUMNS: list[str] = [
    "PLANT_CODE",
    "TAG_NAME",
    "PARENT_TAG_NAME",
    "AREA_CODE",
    "PROCESS_UNIT_CODE",
    "TAG_CLASS_NAME",
    "TAG_STATUS",
    "REQUISITION_CODE",
    "DESIGNED_BY_COMPANY_NAME",
    "COMPANY_NAME",
    "PO_CODE",
    "PRODUCTION_CRITICAL_ITEM",
    "SAFETY_CRITICAL_ITEM",
    "SAFETY_CRITICAL_ITEM_GROUP",
    "SAFETY_CRITICAL_ITEM_REASON_AWARDED",
    "TAG_DESCRIPTION",
    "ACTION_STATUS",
    "ACTION_DATE",
]


def transform_tag_register(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Master Tag Register (seq 003).

    Layers:
    1. Second-level defence: keep only object_status = 'Active' rows.
       (SQL WHERE already filters, this guards against any upstream leak.)
    2. Rename sync_status → ACTION_STATUS.
    3. Convert sync_timestamp → ACTION_DATE (YYYY-MM-DD date only).
    4. Replace PARENT_TAG_NAME literal 'unset' with empty string.
    5. Drop internal columns (object_status, raw sync_status).
    6. Reorder columns to EIS-specified output order.

    Args:
        df: Raw DataFrame from extract_tag_register SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Raises:
        KeyError: If mandatory columns are missing from df.

    Example:
        >>> result = transform_tag_register(raw_df)
        >>> list(result.columns)[:3]
        ['PLANT_CODE', 'TAG_NAME', 'PARENT_TAG_NAME']
    """
    df = _apply_common_eis_transforms(df)

    # Override ACTION_DATE: use last status change from tag_status_history,
    # not sync_timestamp (which reflects last ETL run, not last status change).
    # Source column: action_date_raw (correlated subquery in _TAG_REGISTER_SQL).
    if "ACTION_DATE_RAW" in df.columns:
        derived = (
            pd.to_datetime(df["ACTION_DATE_RAW"], errors="coerce")
            .dt.strftime("%d.%m.%Y")
        )
        # Preserve SYNC_TIMESTAMP-derived ACTION_DATE as fallback for rows
        # where ACTION_DATE_RAW is null (tag has no status history entry).
        df["ACTION_DATE"] = derived.where(derived.notna(), other=df["ACTION_DATE"])
        df["ACTION_DATE"] = df["ACTION_DATE"].fillna("")
        df = df.drop(columns=["ACTION_DATE_RAW"], errors="ignore")

    # Normalise PARENT_TAG_NAME: literal 'unset' → empty string
    df["PARENT_TAG_NAME"] = df["PARENT_TAG_NAME"].replace("unset", "")

    # Reorder to strict EIS column sequence
    available = [c for c in _TAG_REGISTER_COLUMNS if c in df.columns]
    return df[available]


# ---------------------------------------------------------------------------
# Tag Property Values domain transform (seq 303)
# ---------------------------------------------------------------------------

_TAG_PROPERTY_COLUMNS: list[str] = [
    "PLANT_CODE",
    "TAG_NAME",
    "PROPERTY_CODE",
    "PROPERTY_VALUE",
    "UNIT",
]


def transform_tag_properties(df: pd.DataFrame, uom_lookup: dict[str, str] | None = None) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Tag Property Values export (seq 303).

    Layers:
    1. Normalise column names to UPPER_CASE.
    2. Second-level defence: keep only object_status = 'Active' rows.
    3. Split combined value/UoM (e.g., "490mm" → "490", "mm") if uom_lookup provided.
    4. Auto-clear UNIT when PROPERTY_VALUE is NA or TBC.
    5. Drop internal columns used by validation rules (mapping_concept_raw,
       object_id, object_name) and EIS audit columns not in seq-303 schema.
    6. Reorder columns to EIS-specified output order.

    Note: ACTION_STATUS / ACTION_DATE are intentionally excluded from this
    register — property value rows carry no independent sync lifecycle beyond
    the parent tag's. The seq-303 schema specifies only 5 output columns.

    Args:
        df: Raw DataFrame from extract_tag_properties SQL query.
        uom_lookup: Dictionary mapping alias_lower → symbol_ascii for UoM resolution.
                   If None or empty, value/UoM splitting is skipped.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> lookup = {'mm': 'mm', 'bar(g)': 'bar(g)'}
        >>> result = transform_tag_properties(raw_df, uom_lookup=lookup)
        >>> list(result.columns)
        ['PLANT_CODE', 'TAG_NAME', 'PROPERTY_CODE', 'PROPERTY_VALUE', 'UNIT']
    """
    if uom_lookup is None:
        uom_lookup = {}

    df = df.copy()
    df.columns = df.columns.str.upper()

    # Second-level defence: only Active records exported
    if "OBJECT_STATUS" in df.columns:
        df = df[df["OBJECT_STATUS"] == "Active"]

    # Split combined value/UoM if uom_lookup provided
    if uom_lookup and "PROPERTY_VALUE" in df.columns and "UNIT" in df.columns:
        df = _apply_value_uom_split(
            df,
            value_col="PROPERTY_VALUE",
            uom_col="UNIT",
            uom_lookup=uom_lookup,
        )

    # Auto-clear UNIT when PROPERTY_VALUE is NA or TBC
    if "PROPERTY_VALUE" in df.columns and "UNIT" in df.columns:
        mask = df["PROPERTY_VALUE"].fillna("").str.strip().str.upper().isin(["NA", "TBC"])
        df.loc[mask, "UNIT"] = ""

    # Drop all internal/validation helper columns not part of EIS output schema
    internal_cols = [
        "OBJECT_STATUS", "SYNC_STATUS", "SYNC_TIMESTAMP",
        "MAPPING_CONCEPT_RAW", "OBJECT_ID", "OBJECT_NAME",
    ]
    df = df.drop(columns=internal_cols, errors="ignore")

    # Reorder to strict EIS column sequence; silently skip absent columns
    available = [c for c in _TAG_PROPERTY_COLUMNS if c in df.columns]
    return df[available]


# ---------------------------------------------------------------------------
# Equipment Property Values domain transform (seq 301)
# ---------------------------------------------------------------------------

_EQUIPMENT_PROPERTY_COLUMNS: list[str] = [
    "PLANT_CODE",
    "TAG_NAME",
    "PROPERTY_CODE",
    "PROPERTY_VALUE",
    "UNIT",
]


def transform_equipment_properties(df: pd.DataFrame, uom_lookup: dict[str, str] | None = None) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Equipment Property Values export (seq 301).

    Identical column schema to seq-303 but sourced from Physical-concept mappings.
    Equipment properties describe the physical asset, not the functional tag.

    Layers:
    1. Normalise column names to UPPER_CASE.
    2. Second-level defence: keep only object_status = 'Active' rows.
    3. Split combined value/UoM (e.g., "490mm" → "490", "mm") if uom_lookup provided.
    4. Auto-clear UNIT when PROPERTY_VALUE is NA or TBC.
    5. Drop internal columns used by validation rules.
    6. Reorder columns to EIS-specified output order.

    Args:
        df: Raw DataFrame from extract_equipment_properties SQL query.
        uom_lookup: Dictionary mapping alias_lower → symbol_ascii for UoM resolution.
                   If None or empty, value/UoM splitting is skipped.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> lookup = {'mm': 'mm', 'bar(g)': 'bar(g)'}
        >>> result = transform_equipment_properties(raw_df, uom_lookup=lookup)
        >>> list(result.columns)
        ['PLANT_CODE', 'TAG_NAME', 'PROPERTY_CODE', 'PROPERTY_VALUE', 'UNIT']
    """
    if uom_lookup is None:
        uom_lookup = {}

    df = df.copy()
    df.columns = df.columns.str.upper()

    # Second-level defence: only Active records exported
    if "OBJECT_STATUS" in df.columns:
        df = df[df["OBJECT_STATUS"] == "Active"]

    # Split combined value/UoM if uom_lookup provided
    if uom_lookup and "PROPERTY_VALUE" in df.columns and "UNIT" in df.columns:
        df = _apply_value_uom_split(
            df,
            value_col="PROPERTY_VALUE",
            uom_col="UNIT",
            uom_lookup=uom_lookup,
        )

    # Auto-clear UNIT when PROPERTY_VALUE is NA or TBC
    if "PROPERTY_VALUE" in df.columns and "UNIT" in df.columns:
        mask = df["PROPERTY_VALUE"].fillna("").str.strip().str.upper().isin(["NA", "TBC"])
        df.loc[mask, "UNIT"] = ""

    # Drop all internal/validation helper columns not part of EIS output schema
    internal_cols = [
        "OBJECT_STATUS", "SYNC_STATUS", "SYNC_TIMESTAMP",
        "MAPPING_CONCEPT_RAW", "OBJECT_ID", "OBJECT_NAME",
    ]
    df = df.drop(columns=internal_cols, errors="ignore")

    # Reorder to strict EIS column sequence; silently skip absent columns
    available = [c for c in _EQUIPMENT_PROPERTY_COLUMNS if c in df.columns]
    return df[available]


# ---------------------------------------------------------------------------
# Equipment Register domain transform (seq 004)
# ---------------------------------------------------------------------------

_EQUIPMENT_REGISTER_COLUMNS: list[str] = [
    "EQUIPMENT_NUMBER",
    "PLANT_CODE",
    "TAG_NAME",
    "EQUIPMENT_CLASS_NAME",
    "MANUFACTURER_COMPANY_NAME",
    "MODEL_PART_NAME",
    "MANUFACTURER_SERIAL_NUMBER",
    "PURCHASE_DATE",
    "VENDOR_COMPANY_NAME",
    "INSTALLATION_DATE",
    "STARTUP_DATE",
    "PRICE",
    "WARRANTY_END_DATE",
    "PART_OF",
    "TECHIDENTNO",
    "ALIAS",
    "EQUIPMENT_DESCRIPTION",
    "ACTION_STATUS",
    "ACTION_DATE",
]


def transform_equipment_register(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Master Equipment Register (seq 004).

    Layers:
    1. Second-level defence: keep only object_status = 'Active' rows with equip_no set.
       (SQL WHERE already filters, this guards against any upstream leak.)
    2. Compute ACTION_STATUS: Void tag → 'Deleted', otherwise sync_status value.
    3. Convert sync_timestamp → ACTION_DATE (DD.MM.YYYY format).
    4. Drop internal columns (object_status, tag_status, sync_status, sync_timestamp).
    5. Reorder columns to EIS-specified output order.

    Args:
        df: Raw DataFrame from extract_equipment_register SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Raises:
        KeyError: If mandatory columns are missing from df.

    Example:
        >>> result = transform_equipment_register(raw_df)
        >>> list(result.columns)[:3]
        ['EQUIPMENT_NUMBER', 'PLANT_CODE', 'TAG_NAME']
    """
    df = _apply_common_eis_transforms(df)

    # Override ACTION_DATE: use last status change from tag_status_history,
    # not sync_timestamp (which reflects last ETL run, not last status change).
    # Source column: action_date_raw (correlated subquery in _EQUIPMENT_REGISTER_SQL).
    if "ACTION_DATE_RAW" in df.columns:
        derived = (
            pd.to_datetime(df["ACTION_DATE_RAW"], errors="coerce")
            .dt.strftime("%d.%m.%Y")
        )
        # Preserve SYNC_TIMESTAMP-derived ACTION_DATE as fallback for rows
        # where ACTION_DATE_RAW is null (tag has no status history entry).
        df["ACTION_DATE"] = derived.where(derived.notna(), other=df["ACTION_DATE"])
        df["ACTION_DATE"] = df["ACTION_DATE"].fillna("")
        df = df.drop(columns=["ACTION_DATE_RAW"], errors="ignore")

    # Equipment-specific second-level defence: reject rows without equipment number
    df = df[df["EQUIPMENT_NUMBER"].notna() & (df["EQUIPMENT_NUMBER"] != "")]

    # TAG_STATUS is internal; not part of EIS equipment schema
    df = df.drop(columns=["TAG_STATUS"], errors="ignore")

    # Reorder to strict EIS column sequence
    available = [c for c in _EQUIPMENT_REGISTER_COLUMNS if c in df.columns]
    return df[available]


# ---------------------------------------------------------------------------
# Area Register domain transform (seq 203)
# ---------------------------------------------------------------------------

_AREA_REGISTER_COLUMNS: list[str] = [
    "PLANT_CODE",
    "AREA_CODE",
    "AREA_NAME",
    "MAIN_AREA_CODE",
    "PLANT_REF",
]


def transform_area_register(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Area Register export (seq 203).

    Layers:
    1. Normalise column names to UPPER_CASE.
    2. Reorder columns to EIS-specified output order.

    Args:
        df: Raw DataFrame from extract_area_register SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> result = transform_area_register(raw_df)
        >>> list(result.columns)
        ['PLANT_CODE', 'AREA_CODE', 'AREA_NAME', 'MAIN_AREA_CODE', 'PLANT_REF']
    """
    df = df.copy()
    df.columns = df.columns.str.upper()
    available = [c for c in _AREA_REGISTER_COLUMNS if c in df.columns]
    return df[available]


# ---------------------------------------------------------------------------
# Process Unit Register domain transform (seq 204)
# ---------------------------------------------------------------------------

_PROCESS_UNIT_COLUMNS: list[str] = [
    "PLANT_CODE",
    "PROCESS_UNIT_CODE",
    "PROCESS_UNIT_NAME",
    "COUNT_OF_TAGS",
]


def transform_process_unit(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Process Unit Register export (seq 204).

    Layers:
    1. Normalise column names to UPPER_CASE.
    2. Reorder columns to EIS-specified output order.

    Args:
        df: Raw DataFrame from extract_process_unit SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> result = transform_process_unit(raw_df)
        >>> list(result.columns)
        ['PLANT_CODE', 'PROCESS_UNIT_CODE', 'PROCESS_UNIT_NAME', 'COUNT_OF_TAGS']
    """
    df = df.copy()
    df.columns = df.columns.str.upper()
    available = [c for c in _PROCESS_UNIT_COLUMNS if c in df.columns]
    return df[available]


# ---------------------------------------------------------------------------
# Purchase Order Register domain transform (seq 214)
# ---------------------------------------------------------------------------

_PURCHASE_ORDER_COLUMNS: list[str] = [
    "PLANT_CODE",
    "PO_CODE",
    "PO_TITLE",
    "PO_DATE",
    "PO_STATUS",
]


def transform_purchase_order(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Purchase Order Register export (seq 214).

    Layers:
    1. Normalise column names to UPPER_CASE.
    2. Drop raw FK columns used by validation rules (issuer/receiver company raw).
    3. Drop OBJECT_STATUS (already output as PO_STATUS, column aliased in SQL).
    4. Reorder columns to EIS-specified output order.

    Args:
        df: Raw DataFrame from extract_purchase_order SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> result = transform_purchase_order(raw_df)
        >>> list(result.columns)
        ['PLANT_CODE', 'PO_CODE', 'PO_TITLE', 'PO_DATE', 'PO_STATUS']
    """
    df = df.copy()
    df.columns = df.columns.str.upper()
    internal_cols = ["ISSUER_COMPANY_RAW", "RECEIVER_COMPANY_RAW"]
    df = df.drop(columns=internal_cols, errors="ignore")
    available = [c for c in _PURCHASE_ORDER_COLUMNS if c in df.columns]
    return df[available]


# ---------------------------------------------------------------------------
# Model Part Register domain transform (seq 209)
# ---------------------------------------------------------------------------

_MODEL_PART_COLUMNS: list[str] = [
    "MANUFACTURER_COMPANY_NAME",
    "MODEL_PART_NAME",
    "EQUIPMENT_CLASS_NAME",
    "MODEL_DESCRIPTION",
]


def transform_model_part(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Model Part Register export (seq 209).

    Source: project_core.tag joined to reference_core.model_part via tag.model_id.
    FK columns (MANUFACTURER_COMPANY_NAME, EQUIPMENT_CLASS_NAME) are empty string when unresolved.

    Layers:
    1. Normalise column names to UPPER_CASE.
    2. Drop OBJECT_STATUS (already filtered in SQL WHERE clause).
    3. Reorder columns to EIS-specified output order.

    Args:
        df: Raw DataFrame from extract_model_part SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> result = transform_model_part(raw_df)
        >>> list(result.columns)
        ['MANUFACTURER_COMPANY_NAME', 'MODEL_PART_NAME', 'EQUIPMENT_CLASS_NAME', 'MODEL_DESCRIPTION']
    """
    df = df.copy()
    df.columns = df.columns.str.upper()
    df = df.drop(columns=["OBJECT_STATUS"], errors="ignore")
    available = [c for c in _MODEL_PART_COLUMNS if c in df.columns]
    return df[available]


# ---------------------------------------------------------------------------
# Tag Class Properties domain transform (seq 307)
# ---------------------------------------------------------------------------

_TAG_CLASS_PROP_COLUMNS: list[str] = [
    "CLASS_CODE",
    "CLASS_NAME",
    "CONCEPT",
    "PROPERTY_CODE",
    "PROPERTY_NAME",
    "DATA_TYPE",
    "IS_MANDATORY",
    "VALID_VALUES",
    "INSTANCE_COUNT",
]


def transform_tag_class_properties(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Tag Class Properties export (seq 307, file 009).

    Layers:
    1. Normalise column names to UPPER_CASE.
    2. Fill INSTANCE_COUNT NaN → 0, cast to int.
    3. Reorder columns to EIS-specified output order (silently skip absent columns).

    Column schema (exact EIS order):
      CLASS_CODE, CLASS_NAME, CONCEPT, PROPERTY_CODE, PROPERTY_NAME,
      DATA_TYPE, IS_MANDATORY, VALID_VALUES, INSTANCE_COUNT

    Note:
      IS_MANDATORY = 'Y'/'N' (derived in SQL from cp.mapping_presence = 'Mandatory').
      VALID_VALUES = picklist regex from ontology_core.validation_rule (may be empty).
      INSTANCE_COUNT = count of active project_core.tag rows assigned to this class.
      CLASS_NAME was previously called TAG_CLASS_NAME (renamed in 2026-04-11 refactor).

    Args:
        df: Raw DataFrame from extract_tag_class_schema SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> result = transform_tag_class_properties(raw_df)
        >>> list(result.columns)
        ['CLASS_CODE', 'CLASS_NAME', 'CONCEPT', 'PROPERTY_CODE', 'PROPERTY_NAME',
         'DATA_TYPE', 'IS_MANDATORY', 'VALID_VALUES', 'INSTANCE_COUNT']
    """
    df = df.copy()
    df.columns = df.columns.str.upper()
    if "INSTANCE_COUNT" in df.columns:
        df["INSTANCE_COUNT"] = df["INSTANCE_COUNT"].fillna(0).astype(int)
    available = [c for c in _TAG_CLASS_PROP_COLUMNS if c in df.columns]
    return df[available]


# ---------------------------------------------------------------------------
# Tag Instance Property Values — transform for files 010 (Functional) and 011 (Physical)
# ---------------------------------------------------------------------------
# Used by:
#   export_tag_properties_deploy.py        → file 010  (mapping_concept ILIKE '%Functional%')
#   export_equipment_properties_deploy.py  → file 011  (mapping_concept ILIKE '%Physical%')
#
# Column contract (both files — exact EIS order):
#   file 010: PLANT_CODE, TAG_NAME,         PROPERTY_NAME, PROPERTY_VALUE, PROPERTY_VALUE_UOM
#   file 011: PLANT_CODE, EQUIPMENT_NUMBER, PROPERTY_NAME, PROPERTY_VALUE, PROPERTY_VALUE_UOM
#
# PROPERTY_NAME:        human-readable property name (p.name), NOT p.code
# PROPERTY_VALUE_UOM:   symbol_ascii from ontology_core.uom (mixed-case — do NOT uppercase)
#                       Examples: "degC", "kPa(g)", "mm2", "bar(g)"
#
# Value/UoM split responsibility:
#   Detection: VALUE_UOM_COMBINED_IN_CELL rule in audit_core.export_validation_rule
#              (is_builtin=False — logs violations, fix_expression='split_value_uom' is no-op)
#   Actual split: _apply_value_uom_split() below using _P1–_P4 regex patterns
#   Canonical form: _resolve_uom_symbol() → ontology_core.uom_alias (via uom_lookup)

_TAG_INSTANCE_PROP_COLUMNS: list[str] = [
    "PLANT_CODE",
    "TAG_NAME",
    "PROPERTY_NAME",
    "PROPERTY_VALUE",
    "PROPERTY_VALUE_UOM",
]


def transform_tag_instance_properties(
    df: pd.DataFrame,
    uom_lookup: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Transform tag instance property values for EIS files 010 (Functional) / 011 (Physical).

    Pipeline (in order):
      1. Uppercase column names        — PostgreSQL returns lowercase aliases
      2. sanitize_dataframe()          — NaN → "", encoding repair (mojibake etc.)
      3. normalize_pseudo_null()       — PROPERTY_VALUE: sentinel → "NA"
      4. _apply_value_uom_split()      — split embedded UoM (e.g. "490mm" → "490"/"mm")
                                         handles: signed ranges, inch, degree, % LEL
      5. UOM auto-clear                — blank PROPERTY_VALUE_UOM when value is "NA" or "TBC"
      6. Column reorder                — _TAG_INSTANCE_PROP_COLUMNS (exact EIS order)

    UoM case contract:
      PROPERTY_VALUE_UOM is NOT uppercased. Canonical symbols are mixed-case
      (e.g. "degC", "kPa(g)", "mm2"). Upstream alias lookup in _apply_value_uom_split
      resolves raw tokens to canonical form via uom_lookup.

    Args:
        df: Raw DataFrame from _TAG_PROPERTY_VALUES_SQL or _EQUIPMENT_PROPERTY_VALUES_SQL.
        uom_lookup: Dict mapping lower(alias) → symbol_ascii.
                    Loaded once per flow run via _load_uom_lookup(engine).
                    If None or empty, UoM splitting skips alias resolution.

    Returns:
        Transformed DataFrame with exactly 5 columns in EIS-specified order.
        Rows with PROPERTY_VALUE = NULL or "" are excluded at SQL level (not here).

    Example:
        >>> result = transform_tag_instance_properties(raw_df, uom_lookup=lookup)
        >>> list(result.columns)
        ['PLANT_CODE', 'TAG_NAME', 'PROPERTY_NAME', 'PROPERTY_VALUE', 'PROPERTY_VALUE_UOM']
    """
    if uom_lookup is None:
        uom_lookup = {}

    df = df.copy()
    df.columns = df.columns.str.upper()

    # Step 2: encoding repair + NaN → ""
    df = sanitize_dataframe(df)

    # Step 3: normalize pseudo-null sentinels
    if "PROPERTY_VALUE" in df.columns:
        df["PROPERTY_VALUE"] = df["PROPERTY_VALUE"].apply(
            lambda v: normalize_pseudo_null(v) if isinstance(v, str) else v
        )

    # Step 4: split embedded UoM
    # Handles: "490mm", "+60° C", "-50 - 450 Deg C", "6\"", "0% LEL"
    if "PROPERTY_VALUE" in df.columns and "PROPERTY_VALUE_UOM" in df.columns:
        df = _apply_value_uom_split(
            df,
            value_col="PROPERTY_VALUE",
            uom_col="PROPERTY_VALUE_UOM",
            uom_lookup=uom_lookup,
        )
        # Step 5: auto-clear UOM for sentinel and placeholder values
        # NA = pseudo-null (no meaningful value, no meaningful UoM)
        # TBC = to be confirmed (valid export row, UoM would be speculative)
        mask = df["PROPERTY_VALUE"].fillna("").str.strip().str.upper().isin(["NA", "TBC"])
        df.loc[mask, "PROPERTY_VALUE_UOM"] = ""

    # Step 5b: lowercase UOM — canonical EIS format per A36 specification
    if "PROPERTY_VALUE_UOM" in df.columns:
        df["PROPERTY_VALUE_UOM"] = df["PROPERTY_VALUE_UOM"].str.lower()

    available = [c for c in _TAG_INSTANCE_PROP_COLUMNS if c in df.columns]
    return df[available]


_EQUIPMENT_INSTANCE_PROP_COLUMNS: list[str] = [
    "PLANT_CODE",
    "EQUIPMENT_NUMBER",
    "PROPERTY_NAME",
    "PROPERTY_VALUE",
    "PROPERTY_VALUE_UOM",
]


def transform_equipment_instance_properties(
    df: pd.DataFrame,
    uom_lookup: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Transform equipment instance property values for EIS file 011 (Physical).

    Identical pipeline to transform_tag_instance_properties() but selects
    EQUIPMENT_NUMBER (from t.equip_no SQL alias) instead of TAG_NAME.
    EQUIPMENT_NUMBER arrives pre-formatted from SQL as 'Equip_<tag_name>'.

    Pipeline (in order):
      1. Uppercase column names
      2. sanitize_dataframe()          — NaN → "", encoding repair
      3. normalize_pseudo_null()       — PROPERTY_VALUE: sentinel → "NA"
      4. _apply_value_uom_split()      — split embedded UoM
      5. UOM auto-clear                — blank UOM when value is "NA" or "TBC"
      5b. lowercase UOM                — canonical EIS format per A36 specification
      6. Column reorder                — _EQUIPMENT_INSTANCE_PROP_COLUMNS

    Args:
        df: Raw DataFrame from _EQUIPMENT_PROPERTIES_SQL.
        uom_lookup: Dict mapping lower(alias) → symbol_ascii.

    Returns:
        Transformed DataFrame with exactly 5 columns in EIS-specified order.

    Example:
        >>> result = transform_equipment_instance_properties(raw_df, uom_lookup=lookup)
        >>> list(result.columns)
        ['PLANT_CODE', 'EQUIPMENT_NUMBER', 'PROPERTY_NAME', 'PROPERTY_VALUE', 'PROPERTY_VALUE_UOM']
    """
    if uom_lookup is None:
        uom_lookup = {}

    df = df.copy()
    df.columns = df.columns.str.upper()

    # Step 2: encoding repair + NaN → ""
    df = sanitize_dataframe(df)

    # Step 3: normalize pseudo-null sentinels
    if "PROPERTY_VALUE" in df.columns:
        df["PROPERTY_VALUE"] = df["PROPERTY_VALUE"].apply(
            lambda v: normalize_pseudo_null(v) if isinstance(v, str) else v
        )

    # Step 4: split embedded UoM
    if "PROPERTY_VALUE" in df.columns and "PROPERTY_VALUE_UOM" in df.columns:
        df = _apply_value_uom_split(
            df,
            value_col="PROPERTY_VALUE",
            uom_col="PROPERTY_VALUE_UOM",
            uom_lookup=uom_lookup,
        )
        # Step 5: auto-clear UOM for sentinel and placeholder values
        mask = df["PROPERTY_VALUE"].fillna("").str.strip().str.upper().isin(["NA", "TBC"])
        df.loc[mask, "PROPERTY_VALUE_UOM"] = ""

    # Step 5b: lowercase UOM — canonical EIS format per A36 specification
    if "PROPERTY_VALUE_UOM" in df.columns:
        df["PROPERTY_VALUE_UOM"] = df["PROPERTY_VALUE_UOM"].str.lower()

    available = [c for c in _EQUIPMENT_INSTANCE_PROP_COLUMNS if c in df.columns]
    return df[available]


# ---------------------------------------------------------------------------
# Tag Physical Connections domain transform (seq 212)
# ---------------------------------------------------------------------------

_TAG_CONNECTIONS_COLUMNS: list[str] = [
    "PLANT_CODE",
    "FROM_TAG_NAME",
    "TO_TAG_NAME",
]


def transform_tag_connections(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Tag Physical Connections export (seq 212).

    Layers:
    1. Normalise column names to UPPER_CASE.
    2. Reorder columns to EIS-specified output order.

    Args:
        df: Raw DataFrame from extract_tag_connections SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> result = transform_tag_connections(raw_df)
        >>> list(result.columns)
        ['PLANT_CODE', 'FROM_TAG_NAME', 'TO_TAG_NAME']
    """
    df = df.copy()
    df.columns = df.columns.str.upper()

    # Self-loop exclusion moved to SQL level (DISTINCT + from_tag_raw != to_tag_raw)
    # No Python filtering needed here.

    available = [c for c in _TAG_CONNECTIONS_COLUMNS if c in df.columns]
    return df[available]


# ---------------------------------------------------------------------------
# Document Cross-Reference domain transforms (seq 408, 409, 410, 411, 412, 413, 414, 420)
# ---------------------------------------------------------------------------

_DOC_TO_SITE_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "SITE_CODE"]
_DOC_TO_PLANT_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "PLANT_CODE"]
_DOC_TO_PROCESS_UNIT_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "PLANT_CODE", "PROCESS_UNIT_CODE"]
_DOC_TO_AREA_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "AREA_CODE"]
_DOC_TO_TAG_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "PLANT_CODE", "TAG_NAME"]
_DOC_TO_EQUIPMENT_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "PLANT_CODE", "EQUIPMENT_NUMBER"]
_DOC_TO_MODEL_PART_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "PLANT_CODE", "MODEL_PART_CODE"]
_DOC_TO_PO_COLUMNS: list[str] = [
    "DOCUMENT_NUMBER",
    "REVISION_CODE",
    "PO_CODE",
    "PLANT_CODE",
    "COMPANY_NAME",
]

# Shared helper — keeps each transform DRY
def _transform_doc_crossref(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Uppercase columns, drop OBJECT_STATUS, reorder to EIS spec."""
    df = df.copy()
    df.columns = df.columns.str.upper()
    df = df.drop(columns=["OBJECT_STATUS"], errors="ignore")
    available = [c for c in columns if c in df.columns]
    return df[available]


def transform_doc_to_site(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Doc→Site export (seq 408).

    Args:
        df: Raw DataFrame from extract_doc_to_site SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> list(transform_doc_to_site(raw_df).columns)
        ['DOCUMENT_NUMBER', 'SITE_CODE']
    """
    return _transform_doc_crossref(df, _DOC_TO_SITE_COLUMNS)


def transform_doc_to_plant(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Doc→Plant export (seq 409).

    Args:
        df: Raw DataFrame from extract_doc_to_plant SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> list(transform_doc_to_plant(raw_df).columns)
        ['DOCUMENT_NUMBER', 'PLANT_CODE']
    """
    return _transform_doc_crossref(df, _DOC_TO_PLANT_COLUMNS)


def transform_doc_to_process_unit(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Doc→ProcessUnit export (seq 410).

    Source: mapping.tag_document → tag.process_unit_id → process_unit.
    DISTINCT applied in SQL to prevent duplicate (doc, unit) pairs.

    Args:
        df: Raw DataFrame from extract_doc_to_process_unit SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> list(transform_doc_to_process_unit(raw_df).columns)
        ['DOCUMENT_NUMBER', 'PROCESS_UNIT_CODE']
    """
    return _transform_doc_crossref(df, _DOC_TO_PROCESS_UNIT_COLUMNS)


def transform_doc_to_area(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Doc→Area export (seq 411).

    Source: mapping.tag_document → tag.area_id → area.
    DISTINCT applied in SQL to prevent duplicate (doc, area) pairs.

    Args:
        df: Raw DataFrame from extract_doc_to_area SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> list(transform_doc_to_area(raw_df).columns)
        ['DOCUMENT_NUMBER', 'AREA_CODE']
    """
    return _transform_doc_crossref(df, _DOC_TO_AREA_COLUMNS)


def transform_doc_to_tag(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Doc→Tag export (seq 412).

    Args:
        df: Raw DataFrame from extract_doc_to_tag SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> list(transform_doc_to_tag(raw_df).columns)
        ['DOCUMENT_NUMBER', 'PLANT_CODE', 'TAG_NAME']
    """
    return _transform_doc_crossref(df, _DOC_TO_TAG_COLUMNS)


def transform_doc_to_equipment(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Doc→Equipment export (seq 413).

    Only Physical-class tags included (class.concept ILIKE '%Physical%').
    EQUIPMENT_NUMBER sourced from tag.equip_no.

    Args:
        df: Raw DataFrame from extract_doc_to_equipment SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> list(transform_doc_to_equipment(raw_df).columns)
        ['DOCUMENT_NUMBER', 'PLANT_CODE', 'EQUIPMENT_NUMBER']
    """
    return _transform_doc_crossref(df, _DOC_TO_EQUIPMENT_COLUMNS)


def transform_doc_to_model_part(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Doc→ModelPart export (seq 414).

    Source: mapping.tag_document → tag.model_id → model_part.
    DISTINCT applied in SQL to prevent duplicate (doc, model_part) pairs.

    Args:
        df: Raw DataFrame from extract_doc_to_model_part SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> list(transform_doc_to_model_part(raw_df).columns)
        ['DOCUMENT_NUMBER', 'PLANT_CODE', 'MODEL_PART_CODE']
    """
    return _transform_doc_crossref(df, _DOC_TO_MODEL_PART_COLUMNS)


def transform_doc_to_po(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Doc→PurchaseOrder export (seq 420).

    Args:
        df: Raw DataFrame from extract_doc_to_po SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> list(transform_doc_to_po(raw_df).columns)
        ['DOCUMENT_NUMBER', 'REVISION_CODE', 'PO_CODE', 'PLANT_CODE', 'COMPANY_NAME']
    """
    return _transform_doc_crossref(df, _DOC_TO_PO_COLUMNS)
