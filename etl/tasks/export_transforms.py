"""Shared utilities for all Reverse ETL export flows."""

import re
from pathlib import Path

import pandas as pd


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
    s = re.sub(r" {2,}", " ", s)

    # Step 12: Strip leading/trailing whitespace
    s = s.strip()

    # Step 12b: Strip leading/trailing dash artefacts
    # Covers patterns: "- Description", "Description -", "- Description -"
    # Applied after whitespace strip so "- text -" → "text" not "- text -".
    # Only removes edge dashes — internal dashes (e.g. DRAKA/PRYSMIAN - BFOU) are preserved.
    s = s.strip("-").strip()

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


def transform_tag_properties(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Tag Property Values export (seq 303).

    Layers:
    1. Normalise column names to UPPER_CASE.
    2. Second-level defence: keep only object_status = 'Active' rows.
    3. Drop internal columns used by validation rules (mapping_concept_raw,
       object_id, object_name) and EIS audit columns not in seq-303 schema.
    4. Reorder columns to EIS-specified output order.

    Note: ACTION_STATUS / ACTION_DATE are intentionally excluded from this
    register — property value rows carry no independent sync lifecycle beyond
    the parent tag's. The seq-303 schema specifies only 5 output columns.

    Args:
        df: Raw DataFrame from extract_tag_properties SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> result = transform_tag_properties(raw_df)
        >>> list(result.columns)
        ['PLANT_CODE', 'TAG_NAME', 'PROPERTY_CODE', 'PROPERTY_VALUE', 'UNIT']
    """
    df = df.copy()
    df.columns = df.columns.str.upper()

    # Second-level defence: only Active records exported
    if "OBJECT_STATUS" in df.columns:
        df = df[df["OBJECT_STATUS"] == "Active"]

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


def transform_equipment_properties(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Equipment Property Values export (seq 301).

    Identical column schema to seq-303 but sourced from Physical-concept mappings.
    Equipment properties describe the physical asset, not the functional tag.

    Layers:
    1. Normalise column names to UPPER_CASE.
    2. Second-level defence: keep only object_status = 'Active' rows.
    3. Drop internal columns used by validation rules.
    4. Reorder columns to EIS-specified output order.

    Args:
        df: Raw DataFrame from extract_equipment_properties SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> result = transform_equipment_properties(raw_df)
        >>> list(result.columns)
        ['PLANT_CODE', 'TAG_NAME', 'PROPERTY_CODE', 'PROPERTY_VALUE', 'UNIT']
    """
    df = df.copy()
    df.columns = df.columns.str.upper()

    # Second-level defence: only Active records exported
    if "OBJECT_STATUS" in df.columns:
        df = df[df["OBJECT_STATUS"] == "Active"]

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
    "PLANT_CODE",
    "MODEL_PART_CODE",
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
        ['PLANT_CODE', 'MODEL_PART_CODE', 'MANUFACTURER_COMPANY_NAME', 'MODEL_PART_NAME', 'EQUIPMENT_CLASS_NAME', 'MODEL_DESCRIPTION']
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
    "TAG_CLASS_NAME",
    "PROPERTY_CODE",
    "PROPERTY_NAME",
    "DATA_TYPE",
    "IS_MANDATORY",
    "VALID_VALUES",
]


def transform_tag_class_properties(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply domain-specific transforms for EIS Tag Class Properties export (seq 307).

    Layers:
    1. Normalise column names to UPPER_CASE.
    2. Reorder columns to EIS-specified output order.

    Note: IS_MANDATORY = 'Y'/'N' (derived in SQL from mapping_presence = 'Mandatory').
          VALID_VALUES = picklist regex from ontology_core.validation_rule (may be empty).

    Args:
        df: Raw DataFrame from extract_tag_class_properties SQL query.

    Returns:
        Transformed DataFrame ready for write_csv().

    Example:
        >>> result = transform_tag_class_properties(raw_df)
        >>> list(result.columns)
        ['TAG_CLASS_NAME', 'PROPERTY_CODE', 'PROPERTY_NAME', 'DATA_TYPE', 'IS_MANDATORY', 'VALID_VALUES']
    """
    df = df.copy()
    df.columns = df.columns.str.upper()
    available = [c for c in _TAG_CLASS_PROP_COLUMNS if c in df.columns]
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

    # Exclude self-loop connections (FROM_TAG = TO_TAG)
    df = df[df["FROM_TAG_NAME"] != df["TO_TAG_NAME"]]

    available = [c for c in _TAG_CONNECTIONS_COLUMNS if c in df.columns]
    return df[available]


# ---------------------------------------------------------------------------
# Document Cross-Reference domain transforms (seq 408, 409, 410, 411, 412, 413, 414, 420)
# ---------------------------------------------------------------------------

_DOC_TO_SITE_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "SITE_CODE"]
_DOC_TO_PLANT_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "PLANT_CODE"]
_DOC_TO_PROCESS_UNIT_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "PROCESS_UNIT_CODE"]
_DOC_TO_AREA_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "AREA_CODE"]
_DOC_TO_TAG_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "PLANT_CODE", "TAG_NAME"]
_DOC_TO_EQUIPMENT_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "PLANT_CODE", "EQUIPMENT_NUMBER"]
_DOC_TO_MODEL_PART_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "PLANT_CODE", "MODEL_PART_CODE"]
_DOC_TO_PO_COLUMNS: list[str] = ["DOCUMENT_NUMBER", "PLANT_CODE", "PO_CODE"]

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
        ['DOCUMENT_NUMBER', 'PLANT_CODE', 'PO_CODE']
    """
    return _transform_doc_crossref(df, _DOC_TO_PO_COLUMNS)
