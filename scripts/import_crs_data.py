"""
import_crs_data.py

One-shot script: parse CRS (Comment Review Sheet) Excel files and load into
audit_core.crs_comment (PostgreSQL).

Run manually:
    python scripts/import_crs_data.py
    python scripts/import_crs_data.py --debug   # first 5 files only

Parsing logic from scripts/crs_excel_parser.py (tested).
Schema: sql/schema/migration_012_crs_module.sql must be applied first.

Requirements:
    pip install pandas openpyxl python-calamine sqlalchemy pyyaml
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

# Add repo root to path so etl.tasks.common is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from etl.tasks.common import clean_string, load_config, get_db_engine_url, to_dt

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# =============================================================================
# Constants (from scripts/crs_excel_parser.py — tested values)
# =============================================================================

MAIN_PATTERN = re.compile(
    r"^DOC_COMMENT_(JDAW-KVE-E-JA-6944-00001-\d{3}_A\d{2})_[A-Z]{3}\.xlsx$"
)
DETAIL_PATTERN = re.compile(
    r"^(JDAW-KVE-E-JA-6944-00001-\d{3}_A\d{2})(?:_\d+|_Review_Comments)\.xlsx$"
)

COMMENT_COL_KEYWORDS  = ("remark", "adura", "issue", "comment")
PROPERTY_COL_KEYWORDS = ("equipment property name", "tag property name", "property name")
SKIP_SHEETS = {"comment_sheet"}

HASH_EXCLUDE_FIELDS = {
    "sync_timestamp",
    "crs_file_timestamp",
    "llm_response_timestamp",
    "response_approval_date",
    "llm_response",
}

MAX_WORKERS = 14
BATCH_SIZE  = 500


# =============================================================================
# Parsing helpers (from scripts/crs_excel_parser.py)
# =============================================================================

def _scalar(val: Any) -> Any:
    if isinstance(val, pd.Series):
        return val.iloc[0] if not val.empty else None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return val

def _norm_sheet(name: str) -> str:
    return name.strip().lower().replace(" ", "_")

def _revision_label(key: str) -> str:
    """'JDAW-...-019_A28' → 'A28'"""
    m = _REV_RE.search(key)
    return f"A{m.group(1)}" if m else "A00"

_REV_RE = re.compile(r"_A(\d+)")
def _revision_number(key: str) -> int:
    """Extract numeric revision from document key string like '...-019_A28'."""
    m = _REV_RE.search(key)
    return int(m.group(1)) if m else 0

def _expand_merged_cells(ws) -> dict[tuple[int, int], object]:
    cell_map: dict[tuple[int, int], object] = {}
    for row in ws.iter_rows():
        for cell in row:
            cell_map[(cell.row, cell.column)] = cell.value
    for merged_range in ws.merged_cells.ranges:
        min_col, min_row, max_col, max_row = merged_range.bounds
        top_left_val = cell_map.get((min_row, min_col))
        for r in range(min_row, max_row + 1):
            for c in range(min_col, max_col + 1):
                cell_map[(r, c)] = top_left_val
    return cell_map


def _build_two_row_header(cell_map: dict, row1: int, row2: int, max_col: int) -> list[str]:
    headers = []
    for col in range(1, max_col + 1):
        v1 = str(cell_map.get((row1, col), "") or "").strip()
        v2 = str(cell_map.get((row2, col), "") or "").strip()
        if v1 and v2 and v1 != v2:
            name = f"{v1}_{v2}"
        elif v1:
            name = v1
        elif v2:
            name = v2
        else:
            name = f"COL_{col}"
        name = re.sub(r"[\s/\\().,-]+", "_", name).upper().strip("_")
        headers.append(name)
    seen: dict[str, int] = {}
    result = []
    for h in headers:
        if h in seen:
            seen[h] += 1
            result.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            result.append(h)
    return result


def _find_comment_column(ws, data_start_row: int) -> int | None:
    best_span: int = 1
    best_col:  int | None = None
    for merged_range in ws.merged_cells.ranges:
        min_col, min_row, max_col, max_row_range = merged_range.bounds
        if min_col != max_col:
            continue
        if min_row != data_start_row:
            continue
        span = max_row_range - min_row + 1
        if span > best_span:
            best_span = span
            best_col  = min_col - 1
    return best_col


SheetData = tuple[pd.DataFrame, str | None, str | None]


def _load_detail_file_impl(path: Path) -> dict[str, SheetData]:
    result: dict[str, SheetData] = {}
    DATA_START_ROW = 2

    try:
        wb = load_workbook(path, read_only=False, data_only=True)
    except Exception as exc:
        log.error("Cannot open detail file %s: %s", path.name, exc)
        return result

    sheet_names = list(wb.sheetnames)
    sheet_meta: dict[str, tuple[int | None, str | None]] = {}

    for sheet in sheet_names:
        sheet_key = _norm_sheet(sheet)
        if sheet_key in SKIP_SHEETS:
            continue
        ws = wb[sheet]
        comment_col_idx = _find_comment_column(ws, data_start_row=DATA_START_ROW)
        comment_value: str | None = None
        if comment_col_idx is not None:
            raw = ws.cell(row=DATA_START_ROW, column=comment_col_idx + 1).value
            comment_value = str(raw).strip() if raw is not None else None
            comment_value = comment_value or None
        sheet_meta[sheet_key] = (comment_col_idx, comment_value)

    wb.close()

    try:
        xl = pd.ExcelFile(path, engine="calamine")
    except Exception as exc:
        log.error("Cannot open detail file with calamine %s: %s", path.name, exc)
        return result

    for sheet in sheet_names:
        sheet_key = _norm_sheet(sheet)
        if sheet_key not in sheet_meta:
            continue
        comment_col_idx, comment_value = sheet_meta[sheet_key]
        try:
            df = pd.read_excel(xl, sheet_name=sheet, engine="calamine", dtype=str, na_filter=False)
        except Exception:
            continue
        df = df[~df.apply(lambda r: all(v == "" for v in r), axis=1)].copy()
        if df.empty:
            continue
        if comment_col_idx is not None and comment_col_idx < len(df.columns):
            df = df.drop(columns=df.columns[comment_col_idx])
        fallback_comment_col: str | None = None
        if comment_col_idx is None:
            for col in df.columns:
                if any(kw in col.lower() for kw in COMMENT_COL_KEYWORDS):
                    fallback_comment_col = col
                    break
        if fallback_comment_col is not None:
            df = df[df[fallback_comment_col].str.strip() != ""].copy()
            df = df.reset_index(drop=True)
            if df.empty:
                continue
        result[sheet_key] = (df, comment_value, fallback_comment_col)

    return result


_detail_file_cache: dict[Path, dict] = {}
_cache_lock = threading.Lock()


def _load_detail_file(path: Path) -> dict[str, SheetData]:
    if path in _detail_file_cache:
        return _detail_file_cache[path]
    with _cache_lock:
        if path not in _detail_file_cache:
            _detail_file_cache[path] = _load_detail_file_impl(path)
    return _detail_file_cache[path]

def _alphanum(s: str) -> str:
    """Strip all non-alphanumeric chars and lowercase. 'Master Doc' == 'MasterDoc'."""
    return re.sub(r"[^a-z0-9]", "", s.lower())

_EQUIP_PREFIX_RE = re.compile(r"^Equip_(.+)$", re.IGNORECASE)
def _extract_tag_from_equipment(val: Any) -> str | None:
    """
    Extract tag name from equipment number field.
    'Equip_ESB1_BUSCABLE1_0101' → 'ESB1_BUSCABLE1_0101'
    'Equip_JDA-01MV-0047'       → 'JDA-01MV-0047'
    Plain value without prefix  → returned as-is (fallback)
    """
    s = clean_string(val)
    if not s:
        return None
    m = _EQUIP_PREFIX_RE.match(s)
    return m.group(1) if m else s

def _find_tag_col(columns: list[str]) -> tuple[str | None, bool]:
    """
    Returns (col_name, is_equipment_col).
    Priority: tag_name col first, equipment_number col second.
    """
    # Priority 1: column with "tag" but without "property"
    for c in columns:
        cl = c.lower()
        if "tag" in cl and "property" not in cl:
            return c, False

    # Priority 2: column with "equipment" and ("number" or "no")
    for c in columns:
        cl = c.lower()
        if "equipment" in cl and ("number" in cl or "no" in cl):
            return c, True

    return None, False

def find_matching_sheet(
    comment_text: str,
    sheets: dict[str, SheetData],
) -> tuple[str | None, pd.DataFrame | None, str | None, str | None]:
    comment_norm = _alphanum(comment_text)

    # Try exact match first (after normalization)
    for sheet_key, (df, comment_val, fallback_col) in sorted(
        sheets.items(), key=lambda x: len(x[0]), reverse=True
    ):
        if _alphanum(sheet_key) in comment_norm:
            return sheet_key, df, comment_val, fallback_col

    return None, None, None, None

def _report_orphans(orphan_sheets: list[dict]) -> None:
    if not orphan_sheets:
        return

    # Группировка по detail-файлу
    by_file: dict[str, list[dict]] = {}
    for o in orphan_sheets:
        by_file.setdefault(o["detail_file"], []).append(o)

    log.warning("=" * 60)
    log.warning("ORPHAN SHEETS REPORT — %d sheet(s) in %d file(s) not loaded to DB",
                len(orphan_sheets), len(by_file))
    log.warning("=" * 60)

    for detail_file, entries in sorted(by_file.items()):
        # Показать все листы файла — какие совпали, какие нет
        e0 = entries[0]
        log.warning("")
        log.warning("  Detail file : %s", detail_file)
        log.warning("  Main file   : %s", e0["main_file"])
        log.warning("  All sheets  : %s", ", ".join(e0["available_sheets"]))
        log.warning("  Matched     : %s", ", ".join(e0["matched_sheets"]) or "— none —")
        log.warning("  ORPHAN(S)   :")
        for o in entries:
            log.warning("    ✗ sheet='%s'  rows=%d", o["sheet_key"], o["rows"])
            # Подсказка: найти похожие совпавшие комментарии в main-файле
            log.warning("      → sheet normalized: '%s'", _alphanum(o["sheet_key"]))

    log.warning("")
    log.warning("ACTION REQUIRED: Check that GROUP_COMMENT text in main file")
    log.warning("  contains sheet name (after stripping spaces/special chars).")
    log.warning("=" * 60)

def _report_duplicates(dup_by_file: dict[str, int], total_raw: int, total_loaded: int) -> None:
    total_dups = sum(dup_by_file.values())
    if not total_dups:
        log.info("Prepared %d DB records — no duplicates.", total_loaded)
        return

    log.warning("=" * 60)
    log.warning("DUPLICATE RECORDS REPORT — %d duplicate(s) skipped", total_dups)
    log.warning("  Total raw: %d  →  loaded: %d  →  skipped: %d",
                total_raw, total_loaded, total_dups)
    log.warning("  By source file:")
    for src_file, count in sorted(dup_by_file.items(), key=lambda x: -x[1]):
        log.warning("    %-60s  %d dup(s)", src_file, count)
    log.warning("")
    log.warning("ACTION REQUIRED: Duplicates share same comment_id key:")
    log.warning("  crs_doc_number | group_comment | detail_sheet | tag_name | comment | property_name")
    log.warning("  (property_name included only when not null/Not Applicable)")
    log.warning("  Check for repeated rows in listed Excel files.")
    log.warning("=" * 60)

def parse_main_file(path: Path) -> tuple[dict | None, pd.DataFrame | None]:
    try:
        wb = load_workbook(path, read_only=False, data_only=True)
        ws = wb.active
    except Exception as exc:
        log.error("Cannot open %s: %s", path.name, exc)
        return None, None

    cell_map = _expand_merged_cells(ws)
    max_col  = ws.max_column or 0
    wb.close()

    def g(row: int, col: int) -> Any:
        val = cell_map.get((row, col))
        if val is None:
            return None
        try:
            if pd.isna(val):
                return None
        except (TypeError, ValueError):
            pass
        return val

    metadata = {
        "DOC_NUMBER":         g(4, 3),
        "REVISION":           g(3, 6),
        "RETURN_CODE":        g(4, 6),
        "TRANSMITTAL_NUMBER": g(5, 3),
        "TRANSMITTAL_DATE":   g(5, 6),
        "SOURCE_FILE":        path.name,
        "CRS_FILE_PATH":      str(path),
    }

    rc = str(metadata["RETURN_CODE"]).strip().split(".")[0]
    if rc == "1":
        log.info("Skipping %s — Return Code 1.", path.name)
        return None, None

    if max_col < 3:
        return metadata, None

    headers = _build_two_row_header(cell_map, row1=6, row2=7, max_col=max_col)

    try:
        df_raw = pd.read_excel(path, header=None, skiprows=7, engine="calamine", dtype=str, na_filter=False)
    except Exception as exc:
        log.error("Cannot read data rows of %s: %s", path.name, exc)
        return metadata, None

    if df_raw.empty:
        return metadata, None

    actual_cols = df_raw.shape[1]
    if len(headers) < actual_cols:
        headers += [f"COL_{i}" for i in range(len(headers), actual_cols)]
    else:
        headers = headers[:actual_cols]
    df_raw.columns = headers

    col_c_name = headers[2] if len(headers) > 2 else None
    col_f_name = headers[5] if len(headers) > 5 else None
    if col_c_name is None:
        return metadata, None

    df_comments = pd.DataFrame()
    df_comments["GROUP_COMMENT"] = df_raw[col_c_name]
    df_comments["RESPONSE"]      = df_raw[col_f_name] if col_f_name else ""

    col_a_name   = headers[0] if headers else None
    mask_a_empty = (
        df_raw[col_a_name].str.strip() == ""
        if col_a_name else pd.Series([True] * len(df_raw))
    )
    mask_c_empty = df_comments["GROUP_COMMENT"].str.strip() == ""
    df_comments = df_comments[~(mask_a_empty & mask_c_empty)].copy()
    df_comments = df_comments[df_comments["GROUP_COMMENT"].str.strip() != ""].reset_index(drop=True)
    df_comments["RESPONSE"] = df_comments["RESPONSE"].replace("", None)

    return metadata, df_comments


def process_key(
    key: str,
    main_path: Path,
    related_paths: tuple[Path, ...],
) -> tuple[list[dict], list[dict]]:
    records:      list[dict] = []
    matched_keys: set[str]   = set()

    metadata, df_comments = parse_main_file(main_path)
    if metadata is None or df_comments is None:
        return records, []

    all_detail_sheets: dict[Path, dict[str, SheetData]] = {
        p: _load_detail_file(p) for p in related_paths
    }

    for _, row in df_comments.iterrows():
        comment_text  = str(row["GROUP_COMMENT"]).strip()
        response_text = _scalar(row.get("RESPONSE"))
        found_detail  = False

        for detail_path, sheets in all_detail_sheets.items():
            sheet_key, df_sheet, comment_val, fallback_col = find_matching_sheet(comment_text, sheets)
            if df_sheet is None:
                continue

            found_detail = True
            matched_keys.add(f"{detail_path.name}::{sheet_key}")

            # Определить колонки один раз на лист — до цикла по строкам
            tag_col, is_equip_col = _find_tag_col(list(df_sheet.columns))
            prop_col = next(
                (c for c in df_sheet.columns
                 if any(kw in c.lower() for kw in PROPERTY_COL_KEYWORDS)),
                None,
            )

            for _, d_row in df_sheet.iterrows():
                # Tag: через Equip_ strip или напрямую — в зависимости от типа колонки
                raw_tag  = _scalar(d_row[tag_col]) if tag_col else None
                tag_name = (
                    _extract_tag_from_equipment(raw_tag)
                    if is_equip_col
                    else clean_string(raw_tag)
                )

                prop_name = _scalar(d_row[prop_col]) if prop_col else None
                if not prop_name or str(prop_name).strip() == "":
                    prop_name = "Not Applicable"

                row_comment = comment_val
                if row_comment is None and fallback_col and fallback_col in d_row.index:
                    row_comment = _scalar(d_row[fallback_col]) or None

                records.append({
                    "DOC_NUMBER":         metadata.get("DOC_NUMBER"),
                    "REVISION":           metadata.get("REVISION"),
                    "RETURN_CODE":        metadata.get("RETURN_CODE"),
                    "TRANSMITTAL_NUMBER": metadata.get("TRANSMITTAL_NUMBER"),
                    "TRANSMITTAL_DATE":   metadata.get("TRANSMITTAL_DATE"),
                    "TAG_NAME":           tag_name,
                    "PROPERTY_NAME":      prop_name,
                    "GROUP_COMMENT":      comment_text,
                    "RESPONSE":           response_text,
                    "SOURCE_FILE":        metadata.get("SOURCE_FILE"),
                    "DETAIL_FILE":        detail_path.name,
                    "DETAIL_SHEET":       sheet_key,
                    "COMMENT":            row_comment,
                    "CRS_FILE_PATH":      metadata.get("CRS_FILE_PATH"),
                })

            break  # совпадение найдено — не проверять остальные detail-файлы

        if not found_detail:
            records.append({
                "DOC_NUMBER":         metadata.get("DOC_NUMBER"),
                "REVISION":           metadata.get("REVISION"),
                "RETURN_CODE":        metadata.get("RETURN_CODE"),
                "TRANSMITTAL_NUMBER": metadata.get("TRANSMITTAL_NUMBER"),
                "TRANSMITTAL_DATE":   metadata.get("TRANSMITTAL_DATE"),
                "TAG_NAME":           None,
                "PROPERTY_NAME":      "Not Applicable",
                "GROUP_COMMENT":      comment_text,
                "RESPONSE":           response_text,
                "SOURCE_FILE":        metadata.get("SOURCE_FILE"),
                "DETAIL_FILE":        None,
                "DETAIL_SHEET":       None,
                "COMMENT":            "No matching detail sheet found",
                "CRS_FILE_PATH":      metadata.get("CRS_FILE_PATH"),
            })

    orphan_sheets: list[dict] = []
    for detail_path, sheets in all_detail_sheets.items():
        available_sheets   = list(sheets.keys())
        matched_for_file   = [
            mk.split("::")[1]
            for mk in matched_keys
            if mk.startswith(detail_path.name + "::")
        ]
        unmatched_for_file = [sk for sk in available_sheets if sk not in matched_for_file]

        for sk in unmatched_for_file:
            df_orphan, _, _ = sheets[sk]
            orphan_sheets.append({
                "detail_file":      detail_path.name,
                "sheet_key":        sk,
                "rows":             len(df_orphan),
                "main_file":        main_path.name,
                "available_sheets": available_sheets,
                "matched_sheets":   matched_for_file,
            })

    return records, orphan_sheets


# =============================================================================
# DB operations
# =============================================================================

def discover_crs_files(
    root: Path,
) -> tuple[dict[str, Path], dict[str, list[Path]], list[str]]:
    """
    Returns:
        main_files   — {key: path}
        detail_files — {key: [paths]}
        rev_order    — revision keys sorted A01→A99 (e.g. ['A01','A14','A28'])
    """
    main_files:   dict[str, Path]       = {}
    detail_files: dict[str, list[Path]] = {}

    for path in root.rglob("*.xlsx"):
        if "_templates" in path.parts:
            continue
        name = path.name
        m = MAIN_PATTERN.match(name)
        if m:
            key = m.group(1)
            if key not in main_files:
                main_files[key] = path
            else:
                log.warning("Duplicate main key %s — keeping first.", key)
            continue
        d = DETAIL_PATTERN.match(name)
        if d:
            detail_files.setdefault(d.group(1), []).append(path)

    # Группировка по ревизии и сортировка A01→A99
    rev_order = sorted(
        {_revision_label(k) for k in main_files},
        key=lambda r: int(r[1:]) if r[1:].isdigit() else 0,
    )

    log.info(
        "Found %d main file(s) across %d revision(s): %s",
        len(main_files), len(rev_order), ", ".join(rev_order),
    )
    return main_files, detail_files, rev_order


def parse_all_files(
    main_files:   dict[str, Path],
    detail_files: dict[str, list[Path]],
    rev_order:    list[str],
    debug_rev:    str | None = None,     # None = все ревизии
) -> tuple[list[dict], list[str]]:
    """
    Process files grouped by revision, A01 → A99.
    debug_rev: if set, process only this revision group (e.g. 'A28').
    """
    # Сгруппировать ключи по ревизии
    groups: dict[str, list[str]] = {}
    for key in main_files:
        rev = _revision_label(key)
        groups.setdefault(rev, []).append(key)

    revs_to_process = [debug_rev] if debug_rev else rev_order

    all_records:   list[dict] = []
    orphan_sheets: list[dict] = []

    for rev in revs_to_process:
        keys = sorted(groups.get(rev, []))  # внутри ревизии — по имени
        if not keys:
            log.warning("Revision %s requested but no files found.", rev)
            continue

        log.info("── Revision %s: %d file(s) ──", rev, len(keys))

        work_items = [
            (key, main_files[key], tuple(detail_files.get(key, [])))
            for key in keys
        ]

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(process_key, key, main_path, related): key
                for key, main_path, related in work_items
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    records, file_orphans = future.result()
                    all_records.extend(records)
                    orphan_sheets.extend(file_orphans)
                    log.info("  ✓ %s — %d record(s), %d orphan(s)", key, len(records), len(file_orphans))
                except Exception as exc:
                    log.error("  ✗ %s failed: %s", key, exc)

    _detail_file_cache.clear()
    log.info("Parsed %d total records, %d orphan sheets.", len(all_records), len(orphan_sheets))
    return all_records, orphan_sheets


def prepare_crs_records(raw_records: list[dict], engine) -> list[dict]:
    if not raw_records:
        return []

    # ── 1. Collect only needed values for FK lookup ──────────────────────
    needed_tags = {
        clean_string(r.get("TAG_NAME"))
        for r in raw_records
        if clean_string(r.get("TAG_NAME"))
    }

    # ── 2. FK lookup — only for needed values (ANY instead of full scan) ─────
    with engine.connect() as conn:
        tag_lookup: dict[str, str] = {}
        if needed_tags:
            tag_lookup = {
                row.tag_name: str(row.id)
                for row in conn.execute(
                    text("""
                        SELECT id, tag_name
                        FROM project_core.tag
                        WHERE tag_name = ANY(:names)
                          AND object_status = 'Active'
                    """),
                    {"names": list(needed_tags)},
                )
            }

    log.info(
        "FK lookup: %d/%d tags resolved.",
        len(tag_lookup), len(needed_tags),
    )

    # ── 3. Build records ─────────────────────────────────────────────────
    db_records: list[dict] = []
    tag_miss = 0
    seen_comment_ids: set[str] = set()
    dup_by_file: dict[str, int] = {}

    for rec in raw_records:
        # clean_string is called once per field — result is reused
        crs_doc_number    = clean_string(rec.get("DOC_NUMBER")) or "UNKNOWN"
        tag_name          = clean_string(rec.get("TAG_NAME"))
        revision          = clean_string(rec.get("REVISION"))
        return_code       = clean_string(rec.get("RETURN_CODE"))
        transmittal_num   = clean_string(rec.get("TRANSMITTAL_NUMBER"))
        transmittal_date  = to_dt(rec.get("TRANSMITTAL_DATE"))
        group_comment     = clean_string(rec.get("GROUP_COMMENT")) or ""
        comment           = clean_string(rec.get("COMMENT")) or ""
        property_name     = clean_string(rec.get("PROPERTY_NAME"))
        response_vendor   = clean_string(rec.get("RESPONSE"))
        source_file       = clean_string(rec.get("SOURCE_FILE")) or ""
        detail_file       = clean_string(rec.get("DETAIL_FILE"))
        detail_sheet      = clean_string(rec.get("DETAIL_SHEET"))
        crs_file_path     = clean_string(rec.get("CRS_FILE_PATH")) or ""

        # FK resolve
        tag_id = tag_lookup.get(tag_name) if tag_name else None

        if tag_name and not tag_id:
            tag_miss += 1

        # row_hash — from already cleaned values, without calling clean_string again
        hash_source = {
            "crs_doc_number":    crs_doc_number,
            "tag_name":          tag_name or "",
            "revision":          revision or "",
            "return_code":       return_code or "",
            "transmittal_num":   transmittal_num or "",
            "transmittal_date":  str(transmittal_date) if transmittal_date else "",
            "group_comment":     group_comment,
            "comment":           comment,
            "property_name":     property_name or "",
            "response_vendor":   response_vendor or "",
            "source_file":       source_file,
            "detail_file":       detail_file or "",
            "detail_sheet":      detail_sheet or "",
            "crs_file_path":     crs_file_path,
        }
        row_hash = hashlib.md5(
            json.dumps(hash_source, sort_keys=True).encode()
        ).hexdigest()

        # comment_id — deterministic UUID5, no collisions
        prop_key = (
            property_name
            if property_name and property_name.upper() != "NOT APPLICABLE"
            else ""
        )
        comment_id = str(uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{crs_doc_number}|{group_comment}|{detail_sheet or ''}|{tag_name or ''}|{comment}|{prop_key}",
        ))

        # Deduplication within a single batch (protection against duplicates in Excel)
        if comment_id in seen_comment_ids:
            src = clean_string(rec.get("SOURCE_FILE")) or "UNKNOWN"
            dup_by_file[src] = dup_by_file.get(src, 0) + 1
            continue
        seen_comment_ids.add(comment_id)

        db_records.append({
            "comment_id":         comment_id,
            "crs_doc_number":     crs_doc_number,
            "revision":           revision,
            "return_code":        return_code,
            "transmittal_number": transmittal_num,
            "transmittal_date":   transmittal_date,
            "group_comment":      group_comment,
            "comment":            comment,
            "tag_name":           tag_name,
            "tag_id":             tag_id,
            "property_name":      property_name,
            "response_vendor":    response_vendor,
            "source_file":        source_file,
            "detail_file":        detail_file,
            "detail_sheet":       detail_sheet,
            "crs_file_path":      crs_file_path,
            "crs_file_timestamp": None,
            "status":             "RECEIVED",
            "object_status":      "Active",
            "row_hash":           row_hash,
        })

    if tag_miss:
        log.warning("FK miss — tag_name unresolved: %d (tag_id=NULL)", tag_miss)

    _report_duplicates(dup_by_file, len(raw_records), len(db_records))

    return db_records


def upsert_crs_records(engine, records: list[dict], run_id: str) -> dict[str, int]:
    stats = {"inserted": 0, "updated": 0, "errors": 0}
    if not records:
        return stats

    upsert_sql = text("""
        INSERT INTO audit_core.crs_comment (
            comment_id, crs_doc_number, doc_id, revision, return_code,
            transmittal_number, transmittal_date,
            group_comment, comment, tag_name, tag_id, property_name,
            response_vendor, source_file, detail_file, detail_sheet,
            crs_file_path, crs_file_timestamp,
            status, object_status, row_hash, sync_timestamp
        ) VALUES (
            :comment_id, :crs_doc_number, :doc_id, :revision, :return_code,
            :transmittal_number, :transmittal_date,
            :group_comment, :comment, :tag_name, :tag_id, :property_name,
            :response_vendor, :source_file, :detail_file, :detail_sheet,
            :crs_file_path, :crs_file_timestamp,
            :status, :object_status, :row_hash, now()
        )
        ON CONFLICT (comment_id) DO UPDATE SET
            group_comment      = EXCLUDED.group_comment,
            comment            = EXCLUDED.comment,
            tag_name           = EXCLUDED.tag_name,
            tag_id             = EXCLUDED.tag_id,
            doc_id             = EXCLUDED.doc_id,
            property_name      = EXCLUDED.property_name,
            response_vendor    = EXCLUDED.response_vendor,
            crs_file_timestamp = EXCLUDED.crs_file_timestamp,
            row_hash           = EXCLUDED.row_hash,
            sync_timestamp     = now()
        WHERE audit_core.crs_comment.row_hash != EXCLUDED.row_hash
        RETURNING id, xmax
    """)

    audit_sql = text("""
        INSERT INTO audit_core.crs_comment_audit (comment_id, change_type, snapshot, run_id)
        VALUES (:cid, :ct, CAST(:snap AS jsonb), :rid)
    """)

    for batch_start in range(0, len(records), BATCH_SIZE):
        batch = records[batch_start : batch_start + BATCH_SIZE]
        try:
            with engine.begin() as conn:
                audit_rows = []
                for rec in batch:
                    result = conn.execute(upsert_sql, rec)
                    row = result.fetchone()
                    if row is None:
                        continue
                    change_type = "INSERT" if row.xmax == 0 else "UPDATE"
                    if row.xmax == 0:
                        stats["inserted"] += 1
                    else:
                        stats["updated"] += 1
                    snap = {k: str(v) for k, v in rec.items() if v is not None}
                    audit_rows.append({
                        "cid": str(row.id),
                        "ct": change_type,
                        "snap": json.dumps(snap),
                        "rid": run_id,
                    })

                # One executemany instead of N execute:
                if audit_rows:
                    conn.execute(audit_sql, audit_rows)
        except Exception as exc:
            log.error("Batch %d–%d error: %s", batch_start, batch_start + len(batch), exc)
            stats["errors"] += len(batch)

    log.info("Upsert done: inserted=%d updated=%d errors=%d",
             stats["inserted"], stats["updated"], stats["errors"])
    return stats


# =============================================================================
# Main
# =============================================================================

def run(debug_mode: bool = False, debug_rev: str | None = None) -> None:
    run_id = str(uuid.uuid4())
    config  = load_config()
    db_url  = get_db_engine_url(config)

    crs_data_dir = config.get("storage", {}).get("crs_data_dir")
    if not crs_data_dir:
        log.error("storage.crs_data_dir missing from config/config.yaml")
        sys.exit(1)

    root = Path(crs_data_dir)
    if not root.exists():
        log.error("CRS data directory not found: %s", root)
        sys.exit(1)

    log.info("=== CRS Import | run_id=%s | debug=%s ===", run_id, debug_mode)

    engine = create_engine(
        db_url,
        poolclass=QueuePool,
        pool_size=14,        # = MAX_WORKERS
        max_overflow=4,
        pool_recycle=1800,   
        pool_pre_ping=True,  
    )

    # Fail-fast DB check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        log.error("DB connection failed: %s", exc)
        sys.exit(1)

    # Audit: INSERT on start
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO audit_core.sync_run_stats (run_id, target_table, start_time, source_file)
            VALUES (:rid, :tbl, :st, :sf)
        """), {"rid": run_id, "tbl": "audit_core.crs_comment", "st": datetime.now(), "sf": str(root)})

    # Step 1: Discover
    main_files, detail_files, rev_order = discover_crs_files(root)

    active_rev = None
    if debug_mode:
        active_rev = debug_rev or (rev_order[-1] if rev_order else None)
        log.info("DEBUG mode: processing revision %s only.", active_rev)

    all_records, orphan_sheets = parse_all_files(
        main_files, detail_files, rev_order,
        debug_rev=active_rev,
    )

    stats: dict[str, int] = {"inserted": 0, "updated": 0, "errors": 0}

    if all_records:
        # Step 3: Prepare (hash + FK resolution)
        db_records = prepare_crs_records(all_records, engine)

        # Step 4: Upsert
        stats = upsert_crs_records(engine, db_records, run_id)
    else:
        log.warning("No records parsed — nothing to upsert.")

    # Audit: UPDATE on completion
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE audit_core.sync_run_stats SET
                end_time        = :et,
                count_created   = :cr,
                count_updated   = :up,
                count_unchanged = :uc,
                count_deleted   = :dl,
                count_errors    = :er
            WHERE run_id = :rid
        """), {
            "et": datetime.now(),
            "cr": stats["inserted"], "up": stats["updated"],
            "uc": 0, "dl": 0, "er": stats["errors"],
            "rid": run_id,
        })

    engine.dispose()

    _report_orphans(orphan_sheets)

    log.info(
        "=== DONE | parsed=%d loaded=%d errors=%d orphans=%d ===",
        len(all_records), stats["inserted"] + stats["updated"],
        stats["errors"], len(orphan_sheets),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import CRS comments into PostgreSQL")
    parser.add_argument("--debug",     action="store_true")
    parser.add_argument("--debug-rev", default=None,
                        help="Process only this revision group, e.g. A28")
    args = parser.parse_args()
    run(debug_mode=args.debug, debug_rev=args.debug_rev)
