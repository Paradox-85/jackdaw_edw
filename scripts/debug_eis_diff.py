"""
EIS Export Diff Tool
====================
Compares CSV export files from two revision folders side-by-side.

Finds files that exist in BOTH folders (by sequence code, e.g. -010-),
groups them by revision pair (e.g. A36 vs A37), then generates a Markdown
report with:
  - Row count diff + percentage
  - Column name diff
  - Value-level diff statistics per column
  - Per-column value format analysis
  - New / removed / changed row counts (by primary key)
  - Up to 5 concrete row-level diff examples per file

Dev usage (F5 in VS Code — no args needed):
    Edit DEV_FOLDER_A / DEV_FOLDER_B / DEV_OUTPUT below, then run.

CLI usage (overrides dev defaults):
    python tests/test_eis_export_diff.py \\
        --folder-a "C:\\path\\to\\Apr-26\\CSV\\eis_export_A37_20260411_0510" \\
        --folder-b "C:\\path\\to\\Mar-26\\CSV" \\
        --output  "eis_diff_report.md"

Output
------
    Markdown file written to --output (default: DEV_OUTPUT).
    Exit code 0 always (report tool, not a blocker).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


# ---------------------------------------------------------------------------
# Dev defaults — edit these when running locally / debugging in VS Code
# CLI args (--folder-a / --folder-b / --output) override these values
# ---------------------------------------------------------------------------

DEV_FOLDER_A = Path(
    r"C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\EIS\Export for Shell\Apr-26\CSV\eis_export_A37_20260423_0801"
)
DEV_FOLDER_B = Path(
    r"C:\Users\ADZV\OneDrive - Ramboll\Ramboll_Jackdaw - Admin Team\EIS\Export for Shell\Mar-26\CSV"
)
DEV_OUTPUT = Path(__file__).parent / "eis_diff_A37_vs_A36.md"


# ---------------------------------------------------------------------------
# File-specification constants (from docs/file-specification.md)
# ---------------------------------------------------------------------------

# Pattern: JDAW-KVE-E-JA-6944-00001-{SEQ}-{REVISION}.CSV
_FILE_RE = re.compile(
    r"^JDAW-KVE-E-JA-6944-00001-(?P<seq>\d{3})-(?P<rev>[A-Z]\d{2,3})\.CSV$",
    re.IGNORECASE,
)

# Sequence code → human-readable name (from Code Matrix in spec)
SEQ_NAMES: Dict[str, str] = {
    "001": "Site Register (EIS-201)",
    "002": "Plant Register (EIS-202)",
    "003": "Tag Register (EIS-205)",
    "004": "Equipment Register (EIS-206)",
    "005": "Model Part Register (EIS-209)",
    "006": "Tag Physical Connections (EIS-212)",
    "008": "Purchase Order Register (EIS-214)",
    "009": "Tag Class Properties (EIS-307)",
    "010": "Tag Property Values (EIS-303)",
    "011": "Equipment Property Values (EIS-301)",
    "016": "Doc\u2192Tag (EIS-412)",
    "017": "Area Register / Doc\u2192Area (EIS-203/411)",
    "018": "Process Unit Register / Doc\u2192ProcessUnit (EIS-204/410)",
    "019": "Doc\u2192Equipment (EIS-413)",
    "020": "Doc\u2192Model Part (EIS-414)",
    "022": "Doc\u2192Purchase Order (EIS-420)",
    "023": "Doc\u2192Plant (EIS-409)",
    "024": "Doc\u2192Site (EIS-408)",
}

# Primary key columns per sequence (best-effort; used for row identity)
SEQ_PRIMARY_KEYS: Dict[str, List[str]] = {
    "001": ["SITE_CODE"],
    "002": ["PLANT_CODE"],
    "003": ["TAG_NAME"],
    "004": ["EQUIPMENT_NUMBER"],
    "005": ["MODEL_PART_CODE"],
    "006": ["FROM_TAG_NAME", "TO_TAG_NAME"],
    "008": ["PO_CODE"],
    "009": ["TAG_CLASS_NAME", "PROPERTY_CODE"],
    "010": ["TAG_NAME", "PROPERTY_NAME"],
    "011": ["EQUIPMENT_NUMBER", "PROPERTY_NAME"],
    "016": ["DOCUMENT_NUMBER", "TAG_NAME"],
    "017": ["AREA_CODE"],
    "018": ["PROCESS_UNIT_CODE"],
    "019": ["DOCUMENT_NUMBER", "EQUIPMENT_NUMBER"],
    "020": ["DOCUMENT_NUMBER", "MODEL_PART_CODE"],
    "022": ["DOCUMENT_NUMBER", "PO_CODE"],
    "023": ["DOCUMENT_NUMBER"],
    "024": ["DOCUMENT_NUMBER"],
}

# Max row-level diff examples rendered per file
_MAX_ROW_EXAMPLES = 5


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class FileEntry:
    path: Path
    seq: str
    rev: str


@dataclass
class FilePair:
    seq: str
    rev_a: str
    rev_b: str
    path_a: Path
    path_b: Path


@dataclass
class ColumnDiff:
    name: str
    only_in_a: bool = False
    only_in_b: bool = False
    # Value-level stats (filled only for shared columns)
    total_rows: int = 0
    changed_rows: int = 0
    pct_changed: float = 0.0
    unique_a: int = 0
    unique_b: int = 0
    null_a: int = 0
    null_b: int = 0
    sample_changes: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class RowDiffExample:
    """A single concrete row-level diff example.

    pk_values:      dict of PK column → value identifying this row
    changed_cols:   list of (column, value_in_a, value_in_b) for every changed column
    source:         'pk_match' | 'positional' (how the row was matched)
    row_index_a:    positional index in A (only for positional source)
    row_index_b:    positional index in B (only for positional source)
    """
    pk_values: Dict[str, str]
    changed_cols: List[Tuple[str, str, str]]  # (column, val_a, val_b)
    source: str = "pk_match"
    row_index_a: Optional[int] = None
    row_index_b: Optional[int] = None


@dataclass
class PairReport:
    seq: str
    seq_name: str
    rev_a: str
    rev_b: str
    rows_a: int
    rows_b: int
    cols_a: int
    cols_b: int
    row_delta: int
    row_pct: float
    cols_only_in_a: List[str]
    cols_only_in_b: List[str]
    col_diffs: List[ColumnDiff]
    new_rows: int = 0
    removed_rows: int = 0
    changed_rows: int = 0
    pk_used: List[str] = field(default_factory=list)
    row_examples: List[RowDiffExample] = field(default_factory=list)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------


def _scan_folder(folder: Path) -> Dict[str, FileEntry]:
    """Return {seq: FileEntry} for all matching CSV files in folder."""
    result: Dict[str, FileEntry] = {}
    if not folder.exists():
        return result
    for p in sorted(folder.iterdir()):
        if not p.is_file():
            continue
        m = _FILE_RE.match(p.name)
        if not m:
            continue
        seq = m.group("seq")
        rev = m.group("rev").upper()
        result[seq] = FileEntry(path=p, seq=seq, rev=rev)
    return result


def discover_pairs(
    folder_a: Path,
    folder_b: Path,
) -> Tuple[List[FilePair], List[str], List[str]]:
    """Find CSV files present in both folders (matched by sequence code).

    Returns:
        (pairs, only_in_a, only_in_b) — matched pairs plus seq codes that
        exist in only one folder (skipped from comparison).
    """
    map_a = _scan_folder(folder_a)
    map_b = _scan_folder(folder_b)
    common = set(map_a.keys()) & set(map_b.keys())
    only_in_a = sorted(set(map_a.keys()) - set(map_b.keys()))
    only_in_b = sorted(set(map_b.keys()) - set(map_a.keys()))
    pairs = []
    for seq in sorted(common):
        ea = map_a[seq]
        eb = map_b[seq]
        pairs.append(FilePair(
            seq=seq,
            rev_a=ea.rev,
            rev_b=eb.rev,
            path_a=ea.path,
            path_b=eb.path,
        ))
    return pairs, only_in_a, only_in_b


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------


def _load_csv(path: Path) -> pd.DataFrame:
    """Load EIS CSV with correct encoding (utf-8-sig BOM)."""
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )


# ---------------------------------------------------------------------------
# Diff analysis
# ---------------------------------------------------------------------------

_MAX_SAMPLE = 5  # max value-change examples per column


def _analyse_column(
    col: str,
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    pk: Optional[List[str]],
) -> ColumnDiff:
    """Build ColumnDiff for a single shared column, aligned by PK via merge.

    Uses inner merge on PK columns (never set_index) to handle non-unique keys
    safely (e.g. EAV files where TAG_NAME+PROPERTY_CODE may repeat across rows).
    Falls back to positional comparison when no usable PK exists.
    """
    diff = ColumnDiff(name=col)

    ser_a = df_a[col].fillna("")
    ser_b = df_b[col].fillna("")
    diff.null_a = int((ser_a == "").sum())
    diff.null_b = int((ser_b == "").sum())
    diff.unique_a = int(ser_a.nunique())
    diff.unique_b = int(ser_b.nunique())

    valid_pk = [k for k in (pk or []) if k in df_a.columns and k in df_b.columns and k != col]
    if valid_pk:
        # merge-based comparison — safe for non-unique indices
        merged = pd.merge(
            df_a[valid_pk + [col]].rename(columns={col: "_val_a"}),
            df_b[valid_pk + [col]].rename(columns={col: "_val_b"}),
            on=valid_pk,
            how="inner",
        )
        diff.total_rows = len(merged)
        changed = merged[merged["_val_a"] != merged["_val_b"]]
        diff.changed_rows = len(changed)
        diff.pct_changed = (diff.changed_rows / diff.total_rows * 100) if diff.total_rows else 0.0
        for _, row in changed.head(_MAX_SAMPLE).iterrows():
            diff.sample_changes.append((str(row["_val_a"]), str(row["_val_b"])))
    else:
        # positional fallback when no PK available
        min_len = min(len(ser_a), len(ser_b))
        diff.total_rows = min_len
        if min_len > 0:
            a_arr = ser_a.iloc[:min_len].reset_index(drop=True)
            b_arr = ser_b.iloc[:min_len].reset_index(drop=True)
            mask = a_arr != b_arr
            diff.changed_rows = int(mask.sum())
            diff.pct_changed = (diff.changed_rows / min_len * 100) if min_len else 0.0
            for i in a_arr[mask].head(_MAX_SAMPLE).index:
                diff.sample_changes.append((str(a_arr.iloc[i]), str(b_arr.iloc[i])))

    return diff


def _count_changed_rows_by_pk(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    valid_pk: List[str],
    non_pk_cols: List[str],
) -> int:
    """Count rows (matched by PK via merge) where any non-PK column differs.

    Avoids set_index/loc pattern that fails on non-unique PK labels.
    """
    if not non_pk_cols:
        return 0
    merged = pd.merge(
        df_a[valid_pk + non_pk_cols],
        df_b[valid_pk + non_pk_cols],
        on=valid_pk,
        how="inner",
        suffixes=("_a", "_b"),
    )
    if merged.empty:
        return 0
    any_changed = pd.Series(False, index=merged.index)
    for col in non_pk_cols:
        col_a = f"{col}_a"
        col_b = f"{col}_b"
        if col_a in merged.columns and col_b in merged.columns:
            any_changed = any_changed | (merged[col_a].fillna("") != merged[col_b].fillna(""))
    return int(any_changed.sum())


def _build_row_examples_pk(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    valid_pk: List[str],
    non_pk_cols: List[str],
    n: int = _MAX_ROW_EXAMPLES,
) -> List[RowDiffExample]:
    """Return up to n row-level diff examples for files that have a usable PK.

    Strategy:
    - Inner-merge A and B on PK columns.
    - For each merged row where ANY non-PK column differs, record a RowDiffExample
      containing the PK identity and a list of (col, val_a, val_b) for changed cols.
    - Sort changed rows so that rows with the MOST changed columns come first
      (gives the most informative examples at the top).
    """
    if not non_pk_cols or not valid_pk:
        return []

    merged = pd.merge(
        df_a[valid_pk + non_pk_cols],
        df_b[valid_pk + non_pk_cols],
        on=valid_pk,
        how="inner",
        suffixes=("_a", "_b"),
    )
    if merged.empty:
        return []

    # Build per-row change mask
    change_counts = pd.Series(0, index=merged.index)
    for col in non_pk_cols:
        col_a, col_b = f"{col}_a", f"{col}_b"
        if col_a in merged.columns and col_b in merged.columns:
            change_counts += (merged[col_a].fillna("") != merged[col_b].fillna("")).astype(int)

    # Keep only rows where something changed; sort by change_count desc for best examples
    changed_idx = change_counts[change_counts > 0].sort_values(ascending=False).index
    if len(changed_idx) == 0:
        return []

    examples: List[RowDiffExample] = []
    for idx in changed_idx[:n]:
        row = merged.loc[idx]
        pk_values = {pk_col: str(row[pk_col]) for pk_col in valid_pk}
        changed_cols: List[Tuple[str, str, str]] = []
        for col in non_pk_cols:
            col_a, col_b = f"{col}_a", f"{col}_b"
            if col_a in merged.columns and col_b in merged.columns:
                val_a = str(row[col_a]) if pd.notna(row[col_a]) else ""
                val_b = str(row[col_b]) if pd.notna(row[col_b]) else ""
                if val_a != val_b:
                    changed_cols.append((col, val_a, val_b))
        if changed_cols:
            examples.append(RowDiffExample(
                pk_values=pk_values,
                changed_cols=changed_cols,
                source="pk_match",
            ))
    return examples


def _build_row_examples_positional(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    shared_cols: List[str],
    n: int = _MAX_ROW_EXAMPLES,
) -> List[RowDiffExample]:
    """Return up to n row-level diff examples for files without a usable PK.

    Uses positional alignment (row 0 vs row 0, etc.).
    Picks rows with the most changed columns first for maximum insight.
    """
    if not shared_cols:
        return []

    min_len = min(len(df_a), len(df_b))
    if min_len == 0:
        return []

    a_slice = df_a[shared_cols].iloc[:min_len].reset_index(drop=True).fillna("")
    b_slice = df_b[shared_cols].iloc[:min_len].reset_index(drop=True).fillna("")

    # Count how many columns differ per row
    diff_matrix = a_slice != b_slice
    change_counts = diff_matrix.sum(axis=1)
    changed_rows = change_counts[change_counts > 0].sort_values(ascending=False)

    if changed_rows.empty:
        return []

    examples: List[RowDiffExample] = []
    for row_idx in changed_rows.index[:n]:
        changed_cols: List[Tuple[str, str, str]] = []
        for col in shared_cols:
            val_a = str(a_slice.at[row_idx, col])
            val_b = str(b_slice.at[row_idx, col])
            if val_a != val_b:
                changed_cols.append((col, val_a, val_b))
        if changed_cols:
            examples.append(RowDiffExample(
                pk_values={},
                changed_cols=changed_cols,
                source="positional",
                row_index_a=int(row_idx),
                row_index_b=int(row_idx),
            ))
    return examples


def analyse_pair(pair: FilePair) -> PairReport:
    """Perform full diff analysis between two CSV files in the pair."""
    try:
        df_a = _load_csv(pair.path_a)
        df_b = _load_csv(pair.path_b)
    except Exception as exc:  # noqa: BLE001
        return PairReport(
            seq=pair.seq,
            seq_name=SEQ_NAMES.get(pair.seq, pair.seq),
            rev_a=pair.rev_a,
            rev_b=pair.rev_b,
            rows_a=0, rows_b=0, cols_a=0, cols_b=0,
            row_delta=0, row_pct=0.0,
            cols_only_in_a=[], cols_only_in_b=[],
            col_diffs=[],
            error=str(exc),
        )

    cols_a = set(df_a.columns.tolist())
    cols_b = set(df_b.columns.tolist())
    shared_cols = [c for c in df_a.columns if c in cols_b]
    only_a = sorted(cols_a - cols_b)
    only_b = sorted(cols_b - cols_a)

    rows_a = len(df_a)
    rows_b = len(df_b)
    row_delta = rows_b - rows_a
    row_pct = (row_delta / rows_a * 100) if rows_a else 0.0

    pk = SEQ_PRIMARY_KEYS.get(pair.seq, [])
    valid_pk = [k for k in pk if k in cols_a and k in cols_b]

    new_rows = removed_rows = changed_rows_pk = 0
    row_examples: List[RowDiffExample] = []

    if valid_pk:
        keys_a = set(df_a[valid_pk].apply(tuple, axis=1))
        keys_b = set(df_b[valid_pk].apply(tuple, axis=1))
        new_rows = len(keys_b - keys_a)
        removed_rows = len(keys_a - keys_b)
        non_pk_shared = [c for c in shared_cols if c not in valid_pk]
        changed_rows_pk = _count_changed_rows_by_pk(df_a, df_b, valid_pk, non_pk_shared)
        # Build concrete row-level examples (PK-aligned)
        row_examples = _build_row_examples_pk(df_a, df_b, valid_pk, non_pk_shared)
    else:
        # No usable PK — fall back to positional examples
        row_examples = _build_row_examples_positional(df_a, df_b, shared_cols)

    col_diffs = [
        _analyse_column(col, df_a, df_b, pk)
        for col in shared_cols
    ]

    return PairReport(
        seq=pair.seq,
        seq_name=SEQ_NAMES.get(pair.seq, pair.seq),
        rev_a=pair.rev_a,
        rev_b=pair.rev_b,
        rows_a=rows_a,
        rows_b=rows_b,
        cols_a=len(cols_a),
        cols_b=len(cols_b),
        row_delta=row_delta,
        row_pct=row_pct,
        cols_only_in_a=only_a,
        cols_only_in_b=only_b,
        col_diffs=col_diffs,
        new_rows=new_rows,
        removed_rows=removed_rows,
        changed_rows=changed_rows_pk,
        pk_used=valid_pk,
        row_examples=row_examples,
    )


# ---------------------------------------------------------------------------
# Markdown report rendering
# ---------------------------------------------------------------------------

_WARN_ROW_PCT = 5.0   # highlight row-count change above this %
_WARN_COL_PCT = 10.0  # highlight per-column value change above this %

# Truncate long cell values in row-example table to keep it readable
_CELL_MAX_LEN = 80


def _pct_badge(pct: float) -> str:
    if abs(pct) >= _WARN_ROW_PCT:
        return f"**{pct:+.1f}%** ⚠️"
    return f"{pct:+.1f}%"


def _col_pct_badge(pct: float) -> str:
    if pct >= _WARN_COL_PCT:
        return f"**{pct:.1f}%** ⚠️"
    return f"{pct:.1f}%"


def _truncate(s: str, max_len: int = _CELL_MAX_LEN) -> str:
    """Truncate a string for display in a Markdown table cell."""
    s = s.replace("|", "︳")  # escape pipe to avoid breaking table
    if len(s) > max_len:
        return s[:max_len - 1] + "…"
    return s


def _render_row_examples(
    examples: List[RowDiffExample],
    rev_a: str,
    rev_b: str,
    valid_pk: List[str],
) -> List[str]:
    """Render the row-level diff examples section as Markdown lines."""
    if not examples:
        return []

    lines: List[str] = []
    lines.append("#### Row-Level Diff Examples\n")

    source_label = examples[0].source
    if source_label == "positional":
        lines.append(
            "> ⚠️ No shared PK — rows matched **positionally** "
            "(row N in A vs row N in B). May reflect reordering rather than true changes.\n"
        )
    else:
        pk_str = ", ".join(f"`{k}`" for k in valid_pk)
        lines.append(f"> Rows matched by PK: {pk_str}\n")

    for i, ex in enumerate(examples, start=1):
        lines.append(f"**Example {i}**")

        # Identity header
        if ex.source == "pk_match" and ex.pk_values:
            pk_parts = "; ".join(f"`{k}` = `{_truncate(v)}`" for k, v in ex.pk_values.items())
            lines.append(f"  - 🔑 {pk_parts}")
        else:
            lines.append(
                f"  - 🔢 Row #{ex.row_index_a} (0-based positional index)"
            )

        # Changed columns table
        lines.append("")
        lines.append(f"  | Column | Rev A ({rev_a}) | Rev B ({rev_b}) |")
        lines.append("  |--------|:------|:------|")
        for col, val_a, val_b in ex.changed_cols:
            ta = _truncate(val_a)
            tb = _truncate(val_b)
            lines.append(f"  | `{col}` | `{ta}` | `{tb}` |")
        lines.append("")

    return lines


def render_report(
    reports: List[PairReport],
    folder_a: Path,
    folder_b: Path,
    only_in_a: Optional[List[str]] = None,
    only_in_b: Optional[List[str]] = None,
) -> str:
    only_in_a = only_in_a or []
    only_in_b = only_in_b or []
    lines: List[str] = []

    lines.append("# EIS Export Revision Diff Report\n")
    lines.append(f"**Folder A (new):** `{folder_a}`  ")
    lines.append(f"**Folder B (baseline):** `{folder_b}`\n")
    lines.append(f"**Files compared:** {len(reports)}\n")

    lines.append("## Summary\n")
    lines.append("| Seq | Register | Rev A | Rev B | Rows A | Rows B | Δ Rows | % | ⚠️ |")
    lines.append("|-----|----------|-------|-------|-------:|-------:|-------:|--:|---|")
    for r in reports:
        warn = "✅"
        if r.error:
            warn = "💥 ERROR"
        elif abs(r.row_pct) >= _WARN_ROW_PCT or r.cols_only_in_a or r.cols_only_in_b:
            warn = "⚠️"
        lines.append(
            f"| {r.seq} | {r.seq_name} | {r.rev_a} | {r.rev_b} "
            f"| {r.rows_a:,} | {r.rows_b:,} | {r.row_delta:+,} "
            f"| {r.row_pct:+.1f}% | {warn} |"
        )
    for seq in only_in_a:
        name = SEQ_NAMES.get(seq, seq)
        lines.append(f"| {seq} | {name} | — | — | — | — | — | — | 🆕 only in A |")
    for seq in only_in_b:
        name = SEQ_NAMES.get(seq, seq)
        lines.append(f"| {seq} | {name} | — | — | — | — | — | — | ❌ only in B |")

    lines.append("")
    lines.append("---\n")
    lines.append("## Detailed Diff per File\n")

    for r in reports:
        lines.append(f"### {r.seq} — {r.seq_name}")
        lines.append(f"**Revisions:** `{r.rev_a}` (A, new) vs `{r.rev_b}` (B, baseline)\n")

        if r.error:
            lines.append(f"> 💥 **Load error:** `{r.error}`\n")
            continue

        lines.append("#### Row Counts\n")
        lines.append(f"| Metric | Rev A ({r.rev_a}) | Rev B ({r.rev_b}) | Delta |")
        lines.append("|--------|--------:|--------:|------:|")
        lines.append(f"| Total rows | {r.rows_a:,} | {r.rows_b:,} | {_pct_badge(r.row_pct)} |")
        if r.pk_used:
            lines.append(f"| New rows (in B only) | — | {r.new_rows:,} | |")
            lines.append(f"| Removed rows (in A only) | {r.removed_rows:,} | — | |")
            lines.append(f"| Changed rows (same PK) | — | — | {r.changed_rows:,} |")
            lines.append(f"\n> Primary key used: `{'`, `'.join(r.pk_used)}`\n")
        else:
            lines.append("\n> ⚠️ No PK columns available for row-identity analysis.\n")

        lines.append("#### Column Differences\n")
        if not r.cols_only_in_a and not r.cols_only_in_b:
            lines.append("✅ Column sets are identical.\n")
        else:
            if r.cols_only_in_a:
                lines.append(f"**Only in A ({r.rev_a}):** `{'`, `'.join(r.cols_only_in_a)}`\n")
            if r.cols_only_in_b:
                lines.append(f"**Only in B ({r.rev_b}):** `{'`, `'.join(r.cols_only_in_b)}`\n")

        if r.col_diffs:
            lines.append("#### Per-Column Value Statistics\n")
            lines.append(
                "| Column | Unique A | Unique B | Empty A | Empty B "
                "| Changed Rows | % Changed | Samples |"
            )
            lines.append(
                "|--------|--------:|--------:|--------:|--------:"
                "|------------:|----------:|---------|"
            )
            for cd in sorted(r.col_diffs, key=lambda x: -x.pct_changed):
                sample_str = ""
                if cd.sample_changes:
                    parts = [f"`{a}` → `{b}`" for a, b in cd.sample_changes[:3]]
                    sample_str = "; ".join(parts)
                lines.append(
                    f"| `{cd.name}` | {cd.unique_a:,} | {cd.unique_b:,} "
                    f"| {cd.null_a:,} | {cd.null_b:,} "
                    f"| {cd.changed_rows:,} | {_col_pct_badge(cd.pct_changed)} "
                    f"| {sample_str} |"
                )
            lines.append("")

        # Row-level diff examples — most informative section for debugging
        if r.row_examples:
            lines.extend(
                _render_row_examples(r.row_examples, r.rev_a, r.rev_b, r.pk_used)
            )
        else:
            lines.append("#### Row-Level Diff Examples\n")
            lines.append("ℹ️ No row-level differences detected in shared rows.\n")

        lines.append("---\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI — all args are optional; dev defaults used when not provided
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Compare EIS CSV export revisions and generate Markdown diff report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--folder-a",
        default=None,
        metavar="PATH",
        help=f"New export folder (default: DEV_FOLDER_A = {DEV_FOLDER_A})",
    )
    p.add_argument(
        "--folder-b",
        default=None,
        metavar="PATH",
        help=f"Baseline export folder (default: DEV_FOLDER_B = {DEV_FOLDER_B})",
    )
    p.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help=f"Output Markdown report file (default: DEV_OUTPUT = {DEV_OUTPUT})",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    folder_a = Path(args.folder_a) if args.folder_a else DEV_FOLDER_A
    folder_b = Path(args.folder_b) if args.folder_b else DEV_FOLDER_B
    output   = Path(args.output)   if args.output   else DEV_OUTPUT

    print(f"Folder A (new):      {folder_a}")
    print(f"Folder B (baseline): {folder_b}")
    print(f"Output:              {output}")

    if not folder_a.exists():
        print(f"ERROR: folder-a does not exist: {folder_a}")
        return 1
    if not folder_b.exists():
        print(f"ERROR: folder-b does not exist: {folder_b}")
        return 1

    pairs, only_in_a, only_in_b = discover_pairs(folder_a, folder_b)
    if not pairs:
        print("ERROR: No matching CSV pairs found. Check folder paths and file naming.")
        return 1

    print(f"Found {len(pairs)} matching file pair(s): {[p.seq for p in pairs]}")
    if only_in_a:
        print(f"  ⚠️  Files only in folder A (not in B, skipped): {sorted(only_in_a)}")
    if only_in_b:
        print(f"  ⚠️  Files only in folder B (not in A, skipped): {sorted(only_in_b)}")

    reports: List[PairReport] = []
    for pair in pairs:
        print(f"  Analysing seq={pair.seq} ({pair.rev_a} vs {pair.rev_b}) ...", end=" ")
        report = analyse_pair(pair)
        reports.append(report)
        status = "ERROR" if report.error else (
            f"Δrows={report.row_delta:+,}  examples={len(report.row_examples)}"
        )
        print(status)

    md = render_report(reports, folder_a, folder_b, only_in_a, only_in_b)
    output.write_text(md, encoding="utf-8")
    print(f"\nReport written to: {output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
