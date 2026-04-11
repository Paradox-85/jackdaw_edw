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

Usage
-----
    python tests/test_eis_export_diff.py \\
        --folder-a "C:\\path\\to\\Apr-26\\CSV\\eis_export_A37_20260411_0510" \\
        --folder-b "C:\\path\\to\\Mar-26\\CSV" \\
        --output  "eis_diff_report.md"

Output
------
    Markdown file written to --output (default: eis_diff_report.md).
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
# File-specification constants (from docs/file-specification.md)
# ---------------------------------------------------------------------------

# Pattern: JDAW-KVE-E-JA-6944-00001-{SEQ}-{REVISION}.CSV
_FILE_RE = re.compile(
    r"^JDAW-KVE-E-JA-6944-00001-(?P<seq>\d{3})-(?P<rev>[A-Z]\d{2,3})\.CSV$",
    re.IGNORECASE,
)

# Sequence code → human-readable name (from Code Matrix in spec)
SEQ_NAMES: Dict[str, str] = {
    "003": "Tag Register (EIS-205)",
    "004": "Equipment Register (EIS-206)",
    "005": "Model Part Register (EIS-209)",
    "006": "Tag Physical Connections (EIS-212)",
    "008": "Purchase Order Register (EIS-214)",
    "009": "Tag Class Properties (EIS-307)",
    "010": "Tag Property Values (EIS-303)",
    "011": "Equipment Property Values (EIS-301)",
    "016": "Doc→Tag (EIS-412)",
    "017": "Area Register / Doc→Area (EIS-203/411)",
    "018": "Process Unit Register / Doc→ProcessUnit (EIS-204/410)",
    "019": "Doc→Equipment (EIS-413)",
    "020": "Doc→Model Part (EIS-414)",
    "022": "Doc→Purchase Order (EIS-420)",
    "023": "Doc→Plant (EIS-409)",
    "024": "Doc→Site (EIS-408)",
}

# Primary key columns per sequence (best-effort; used for row identity)
SEQ_PRIMARY_KEYS: Dict[str, List[str]] = {
    "003": ["TAG_NAME"],
    "004": ["EQUIPMENT_NUMBER"],
    "005": ["MODEL_PART_CODE"],
    "006": ["FROM_TAG_NAME", "TO_TAG_NAME"],
    "008": ["PO_CODE"],
    "009": ["TAG_CLASS_NAME", "PROPERTY_CODE"],
    "010": ["TAG_NAME", "PROPERTY_CODE"],
    "011": ["TAG_NAME", "PROPERTY_CODE"],
    "016": ["DOCUMENT_NUMBER", "TAG_NAME"],
    "017": ["AREA_CODE"],
    "018": ["PROCESS_UNIT_CODE"],
    "019": ["DOCUMENT_NUMBER", "EQUIPMENT_NUMBER"],
    "020": ["DOCUMENT_NUMBER", "MODEL_PART_CODE"],
    "022": ["DOCUMENT_NUMBER", "PO_CODE"],
    "023": ["DOCUMENT_NUMBER"],
    "024": ["DOCUMENT_NUMBER"],
}


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
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------


def _scan_folder(folder: Path) -> Dict[str, FileEntry]:
    """Return {seq: FileEntry} for all matching CSV files in folder."""
    result: Dict[str, FileEntry] = {}
    if not folder.exists():
        return result
    for p in folder.glob("*.CSV"):
        m = _FILE_RE.match(p.name)
        if not m:
            # Try case-insensitive search for .csv extension
            pass
        if not m:
            for p2 in folder.glob("*.csv"):
                m2 = _FILE_RE.match(p2.name)
                if m2:
                    seq = m2.group("seq")
                    rev = m2.group("rev").upper()
                    result[seq] = FileEntry(path=p2, seq=seq, rev=rev)
            break
        seq = m.group("seq")
        rev = m.group("rev").upper()
        result[seq] = FileEntry(path=p, seq=seq, rev=rev)
    # Also check .csv (lowercase extension)
    if not result:
        for p in folder.glob("*.csv"):
            m = _FILE_RE.match(p.name)
            if m:
                seq = m.group("seq")
                rev = m.group("rev").upper()
                result[seq] = FileEntry(path=p, seq=seq, rev=rev)
    return result


def discover_pairs(folder_a: Path, folder_b: Path) -> List[FilePair]:
    """Find CSV files present in both folders (matched by sequence code)."""
    map_a = _scan_folder(folder_a)
    map_b = _scan_folder(folder_b)
    common = set(map_a.keys()) & set(map_b.keys())
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
    return pairs


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
    """Build ColumnDiff for a single shared column, aligned by PK if available."""
    diff = ColumnDiff(name=col)

    ser_a = df_a[col].fillna("")
    ser_b = df_b[col].fillna("")
    diff.null_a = (df_a[col] == "").sum()
    diff.null_b = (df_b[col] == "").sum()
    diff.unique_a = ser_a.nunique()
    diff.unique_b = ser_b.nunique()

    # Align by PK for value comparison
    valid_pk = [k for k in (pk or []) if k in df_a.columns and k in df_b.columns and k != col]
    if valid_pk:
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
        # Fall back to positional comparison (shorter length)
        min_len = min(len(ser_a), len(ser_b))
        diff.total_rows = min_len
        if min_len > 0:
            a_arr = ser_a.iloc[:min_len].reset_index(drop=True)
            b_arr = ser_b.iloc[:min_len].reset_index(drop=True)
            mask = a_arr != b_arr
            diff.changed_rows = mask.sum()
            diff.pct_changed = (diff.changed_rows / min_len * 100) if min_len else 0.0
            for i in a_arr[mask].head(_MAX_SAMPLE).index:
                diff.sample_changes.append((str(a_arr.iloc[i]), str(b_arr.iloc[i])))

    return diff


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

    # Row-level identity analysis
    new_rows = removed_rows = changed_rows_pk = 0
    if valid_pk:
        keys_a = set(df_a[valid_pk].apply(tuple, axis=1))
        keys_b = set(df_b[valid_pk].apply(tuple, axis=1))
        new_rows = len(keys_b - keys_a)
        removed_rows = len(keys_a - keys_b)
        common_keys = keys_a & keys_b
        if common_keys and shared_cols:
            sub_a = df_a[df_a[valid_pk].apply(tuple, axis=1).isin(common_keys)].set_index(valid_pk)
            sub_b = df_b[df_b[valid_pk].apply(tuple, axis=1).isin(common_keys)].set_index(valid_pk)
            non_pk_shared = [c for c in shared_cols if c not in valid_pk]
            if non_pk_shared:
                sub_a_s = sub_a[non_pk_shared].sort_index()
                sub_b_s = sub_b[non_pk_shared].sort_index()
                common_idx = sub_a_s.index.intersection(sub_b_s.index)
                if len(common_idx):
                    changed_rows_pk = int(
                        (sub_a_s.loc[common_idx] != sub_b_s.loc[common_idx]).any(axis=1).sum()
                    )

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
    )


# ---------------------------------------------------------------------------
# Markdown report rendering
# ---------------------------------------------------------------------------

_WARN_ROW_PCT = 5.0   # highlight row-count change above this %
_WARN_COL_PCT = 10.0  # highlight per-column value change above this %


def _pct_badge(pct: float) -> str:
    if abs(pct) >= _WARN_ROW_PCT:
        return f"**{pct:+.1f}%** ⚠️"
    return f"{pct:+.1f}%"


def _col_pct_badge(pct: float) -> str:
    if pct >= _WARN_COL_PCT:
        return f"**{pct:.1f}%** ⚠️"
    return f"{pct:.1f}%"


def render_report(
    reports: List[PairReport],
    folder_a: Path,
    folder_b: Path,
) -> str:
    lines: List[str] = []

    lines.append("# EIS Export Revision Diff Report\n")
    lines.append(f"**Folder A (new):** `{folder_a}`  ")
    lines.append(f"**Folder B (baseline):** `{folder_b}`\n")
    lines.append(f"**Files compared:** {len(reports)}\n")

    # Summary table
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

    lines.append("")

    # Detailed section per file
    lines.append("---\n")
    lines.append("## Detailed Diff per File\n")

    for r in reports:
        lines.append(f"### {r.seq} — {r.seq_name}")
        lines.append(f"**Revisions:** `{r.rev_a}` (A, new) vs `{r.rev_b}` (B, baseline)\n")

        if r.error:
            lines.append(f"> 💥 **Load error:** `{r.error}`\n")
            continue

        # --- Row counts ---
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

        # --- Column diffs ---
        lines.append("#### Column Differences\n")
        if not r.cols_only_in_a and not r.cols_only_in_b:
            lines.append("✅ Column sets are identical.\n")
        else:
            if r.cols_only_in_a:
                lines.append(f"**Only in A ({r.rev_a}):** `{'`, `'.join(r.cols_only_in_a)}`\n")
            if r.cols_only_in_b:
                lines.append(f"**Only in B ({r.rev_b}):** `{'`, `'.join(r.cols_only_in_b)}`\n")

        # --- Per-column value stats ---
        if r.col_diffs:
            lines.append("#### Per-Column Value Statistics\n")
            lines.append(
                f"| Column | Unique A | Unique B | Empty A | Empty B "
                f"| Changed Rows | % Changed | Samples |"
            )
            lines.append(
                "|--------|--------:|--------:|--------:|--------:|"
                "------------:|----------:|---------|"
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

        lines.append("---\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Compare EIS CSV export revisions and generate Markdown diff report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--folder-a",
        required=True,
        metavar="PATH",
        help="Path to first (new) export folder, e.g. .../Apr-26/CSV/eis_export_A37_...",
    )
    p.add_argument(
        "--folder-b",
        required=True,
        metavar="PATH",
        help="Path to second (baseline) export folder, e.g. .../Mar-26/CSV",
    )
    p.add_argument(
        "--output",
        default="eis_diff_report.md",
        metavar="FILE",
        help="Output Markdown report file path (default: eis_diff_report.md)",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    folder_a = Path(args.folder_a)
    folder_b = Path(args.folder_b)
    output = Path(args.output)

    print(f"Scanning folder A: {folder_a}")
    print(f"Scanning folder B: {folder_b}")

    pairs = discover_pairs(folder_a, folder_b)
    if not pairs:
        print("ERROR: No matching CSV pairs found. Check folder paths and file naming.")
        return 1

    print(f"Found {len(pairs)} matching file pair(s): {[p.seq for p in pairs]}")

    reports: List[PairReport] = []
    for pair in pairs:
        print(f"  Analysing seq={pair.seq} ({pair.rev_a} vs {pair.rev_b}) ...", end=" ")
        report = analyse_pair(pair)
        reports.append(report)
        status = "ERROR" if report.error else f"Δrows={report.row_delta:+,}"
        print(status)

    md = render_report(reports, folder_a, folder_b)
    output.write_text(md, encoding="utf-8")
    print(f"\nReport written to: {output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
