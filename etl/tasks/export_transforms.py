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

    # Step 11: Collapse multiple spaces to single
    s = re.sub(r" {2,}", " ", s)

    # Step 12: Strip leading/trailing whitespace
    return s.strip()


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
                lambda x: clean_engineering_text(x) if isinstance(x, str) else x
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

    # Sanitize encoding artefacts before writing — mandatory, cannot be skipped
    clean_df = sanitize_dataframe(df)
    clean_df.to_csv(path, index=False, encoding="utf-8-sig")
    return len(clean_df)


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
    # Second-level defence: only Active records exported
    df = df[df["object_status"] == "Active"].copy()

    # Rename sync control columns to EIS output names
    df = df.rename(columns={"sync_status": "ACTION_STATUS"})

    # Convert timestamp to date-only string for EIS format
    df["ACTION_DATE"] = pd.to_datetime(df["sync_timestamp"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Normalise PARENT_TAG_NAME: literal 'unset' → empty string
    df["PARENT_TAG_NAME"] = df["PARENT_TAG_NAME"].replace("unset", "")

    # Drop internal columns not exported to EIS
    df = df.drop(columns=["object_status", "sync_timestamp"], errors="ignore")

    # Reorder to strict EIS column sequence
    available = [c for c in _TAG_REGISTER_COLUMNS if c in df.columns]
    return df[available]
