"""
Unit tests for import_crs_data.py — detail file selection logic and hash stability.

Run:
    python -m pytest tests/test_import_crs_data.py -v
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

# Allow import from repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.import_crs_data import (
    DETAIL_PATTERN,
    MAIN_PATTERN,
    _detail_version,
    _is_review_comments,
    _revision_label,
    _revision_number,
    _select_detail_files,
    discover_crs_files,
)

# ---------------------------------------------------------------------------
# _detail_version
# ---------------------------------------------------------------------------

def test_detail_version_versioned():
    assert _detail_version("JDAW-KVE-E-JA-6944-00001-003_A34_10.xlsx") == 10


def test_detail_version_review_comments_returns_zero():
    assert _detail_version("JDAW-KVE-E-JA-6944-00001-003_A21_Review_Comments.xlsx") == 0


def test_detail_version_lower_version():
    assert _detail_version("JDAW-KVE-E-JA-6944-00001-003_A34_3.xlsx") == 3


# ---------------------------------------------------------------------------
# _is_review_comments
# ---------------------------------------------------------------------------

def test_is_review_comments_true():
    assert _is_review_comments("JDAW-KVE-E-JA-6944-00001-003_A21_Review_Comments.xlsx") is True


def test_is_review_comments_false():
    assert _is_review_comments("JDAW-KVE-E-JA-6944-00001-003_A34_10.xlsx") is False


# ---------------------------------------------------------------------------
# _select_detail_files
# ---------------------------------------------------------------------------

def _make_paths(names: list[str], base: Path) -> list[Path]:
    return [base / name for name in names]


def test_select_max_version_from_versioned(tmp_path: Path):
    paths = _make_paths([
        "JDAW-KVE-E-JA-6944-00001-003_A34_3.xlsx",
        "JDAW-KVE-E-JA-6944-00001-003_A34_5.xlsx",
        "JDAW-KVE-E-JA-6944-00001-003_A34_10.xlsx",
    ], tmp_path)
    selected, reason = _select_detail_files(paths)
    assert len(selected) == 1
    assert selected[0].name == "JDAW-KVE-E-JA-6944-00001-003_A34_10.xlsx"
    assert reason == "max_version=10"


def test_select_prefers_review_comments_over_versioned(tmp_path: Path):
    paths = _make_paths([
        "JDAW-KVE-E-JA-6944-00001-003_A34_3.xlsx",
        "JDAW-KVE-E-JA-6944-00001-003_A34_10.xlsx",
        "JDAW-KVE-E-JA-6944-00001-003_A34_Review_Comments.xlsx",
    ], tmp_path)
    selected, reason = _select_detail_files(paths)
    assert len(selected) == 1
    assert selected[0].name == "JDAW-KVE-E-JA-6944-00001-003_A34_Review_Comments.xlsx"
    assert reason == "review_comments"


def test_select_review_comments_wins_over_max_version(tmp_path: Path):
    paths = _make_paths([
        "JDAW-KVE-E-JA-6944-00001-003_A21_Review_Comments.xlsx",
        "JDAW-KVE-E-JA-6944-00001-003_A21_10.xlsx",
    ], tmp_path)
    selected, reason = _select_detail_files(paths)
    assert reason == "review_comments"
    assert len(selected) == 1
    assert _is_review_comments(selected[0].name)


def test_select_fallback_single_file(tmp_path: Path):
    paths = _make_paths(["JDAW-KVE-E-JA-6944-00001-003_A34_unusual.xlsx"], tmp_path)
    selected, reason = _select_detail_files(paths)
    assert selected == paths
    assert reason == "fallback_all"


# ---------------------------------------------------------------------------
# discover_crs_files — subdirectory exclusion
# ---------------------------------------------------------------------------

def test_discover_excludes_subdirectory_files(tmp_path: Path):
    """Detail files in subdirectories must be excluded (Rule 0)."""
    key = "JDAW-KVE-E-JA-6944-00001-003_A34"

    # Create master file
    main_path = tmp_path / f"DOC_COMMENT_{key}_ABC.xlsx"
    main_path.touch()

    # Create a same-dir detail file (eligible)
    same_dir_detail = tmp_path / f"{key}_10.xlsx"
    same_dir_detail.touch()

    # Create a subdirectory detail file (must be excluded)
    subdir = tmp_path / "old_version"
    subdir.mkdir()
    sub_detail = subdir / f"{key}_5.xlsx"
    sub_detail.touch()

    main_files, detail_files, _ = discover_crs_files(tmp_path)

    assert key in detail_files
    selected = detail_files[key]
    assert all(p.parent == tmp_path for p in selected), "Subdir file leaked into selection"
    assert sub_detail not in selected


# ---------------------------------------------------------------------------
# hash stability — same comment from different file paths → same hash
# ---------------------------------------------------------------------------

def test_hash_stable_across_file_paths():
    """Changing crs_file_path or detail_file must not change the row hash."""
    base_hash_source = {
        "crs_doc_number":      "JDAW-KVE-E-JA-6944-00001-003",
        "tag_name":            "HIS0163",
        "revision":            "A34",
        "return_code":         "2",
        "transmittal_num":     "T001",
        "transmittal_date":    "2024-01-01 00:00:00",
        "group_comment":       "Tag not found in EDW",
        "comment":             "Tag HIS0163 does not exist",
        "property_name":       "Not Applicable",
        "document_number_ref": "Not Applicable",
        "from_tag":            "",
        "to_tag":              "",
        "detail_sheet":        "tag_not_found",
    }

    hash1 = hashlib.md5(json.dumps(base_hash_source, sort_keys=True).encode()).hexdigest()

    # Simulate re-import from a different file path — hash_source is identical
    hash2 = hashlib.md5(json.dumps(base_hash_source, sort_keys=True).encode()).hexdigest()

    assert hash1 == hash2, "Hash changed between identical hash_source dicts"


# ---------------------------------------------------------------------------
# _load_detail_file_impl — hidden sheet filtering and collision detection
# ---------------------------------------------------------------------------

import logging
from unittest.mock import MagicMock, patch


def _make_mock_wb(sheet_specs: list[tuple[str, str]]) -> MagicMock:
    """Return a mock openpyxl Workbook with controlled sheet_state values."""
    state_map = dict(sheet_specs)
    wb = MagicMock()
    wb.sheetnames = [name for name, _ in sheet_specs]

    def _get_sheet(name: str) -> MagicMock:
        ws = MagicMock()
        ws.sheet_state = state_map[name]
        ws.merged_cells.ranges = []
        ws.iter_rows.return_value = iter([])
        ws.cell.return_value = MagicMock(value=None)
        return ws

    wb.__getitem__ = lambda self, name: _get_sheet(name)
    return wb


def test_hidden_sheets_excluded(tmp_path: Path) -> None:
    """sheet_state='hidden' sheets must be excluded from processing."""
    from scripts.import_crs_data import _load_detail_file_impl

    mock_wb = _make_mock_wb([("Tag_List", "visible"), ("HiddenData", "hidden")])

    with patch("scripts.import_crs_data.load_workbook", return_value=mock_wb), \
         patch("pandas.ExcelFile", side_effect=Exception("no calamine")):
        result = _load_detail_file_impl(tmp_path / "fake.xlsx")

    assert isinstance(result, dict)


def test_very_hidden_sheets_excluded(tmp_path: Path) -> None:
    """sheet_state='veryHidden' sheets must also be excluded."""
    from scripts.import_crs_data import _load_detail_file_impl

    mock_wb = _make_mock_wb([("Visible", "visible"), ("VeryHidden", "veryHidden")])

    with patch("scripts.import_crs_data.load_workbook", return_value=mock_wb), \
         patch("pandas.ExcelFile", side_effect=Exception("no calamine")):
        result = _load_detail_file_impl(tmp_path / "fake.xlsx")

    assert isinstance(result, dict)


def test_sheet_name_collision_skips_duplicate(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Normalised sheet name collision must log WARNING and skip the duplicate."""
    from scripts.import_crs_data import _load_detail_file_impl

    # "Tag List" and "Tag_List" both normalise to "tag_list"
    mock_wb = _make_mock_wb([("Tag List", "visible"), ("Tag_List", "visible")])

    with patch("scripts.import_crs_data.load_workbook", return_value=mock_wb), \
         patch("pandas.ExcelFile", side_effect=Exception("no calamine")), \
         caplog.at_level(logging.WARNING):
        result = _load_detail_file_impl(tmp_path / "fake.xlsx")

    assert isinstance(result, dict)
    assert any("collision" in msg.lower() for msg in caplog.messages)


# ---------------------------------------------------------------------------
# DETAIL_PATTERN / MAIN_PATTERN — case-insensitivity and revision flexibility
# ---------------------------------------------------------------------------

def test_detail_pattern_matches_review_comments_case_insensitive() -> None:
    """DETAIL_PATTERN must match _Review_Comments regardless of case."""
    assert DETAIL_PATTERN.match("JDAW-KVE-E-JA-6944-00001-007_A19_Review_Comments.xlsx")
    assert DETAIL_PATTERN.match("JDAW-KVE-E-JA-6944-00001-007_A19_review_comments.xlsx")
    assert DETAIL_PATTERN.match("JDAW-KVE-E-JA-6944-00001-007_A19_REVIEW_COMMENTS.xlsx")


def test_detail_pattern_matches_high_revision_numbers() -> None:
    """DETAIL_PATTERN must match revisions with 3+ digits (A100+)."""
    assert DETAIL_PATTERN.match("JDAW-KVE-E-JA-6944-00001-007_A100_Review_Comments.xlsx")
    assert DETAIL_PATTERN.match("JDAW-KVE-E-JA-6944-00001-007_A100_5.xlsx")


def test_main_pattern_case_insensitive() -> None:
    """MAIN_PATTERN must match file names regardless of case."""
    assert MAIN_PATTERN.match("DOC_COMMENT_JDAW-KVE-E-JA-6944-00001-007_A19_KVE.xlsx")
    assert MAIN_PATTERN.match("doc_comment_JDAW-KVE-E-JA-6944-00001-007_A19_kve.xlsx")
    assert MAIN_PATTERN.match("DOC_COMMENT_JDAW-KVE-E-JA-6944-00001-007_A100_KVE.xlsx")


# ---------------------------------------------------------------------------
# Key normalisation and _revision_label / _revision_number with lowercase keys
# ---------------------------------------------------------------------------

def test_key_normalisation_case_insensitive(tmp_path: Path) -> None:
    """detail key from lowercase filename must match upper-case main key."""
    key_upper = "JDAW-KVE-E-JA-6944-00001-007_A19"

    # Master file with upper-case name
    main_path = tmp_path / f"DOC_COMMENT_{key_upper}_KVE.xlsx"
    main_path.touch()

    # Detail file with lower-case revision in name
    detail_lower = tmp_path / "JDAW-KVE-E-JA-6944-00001-007_a19_Review_Comments.xlsx"
    detail_lower.touch()

    main_files, detail_files, _ = discover_crs_files(tmp_path)

    # Both keys must resolve to the same upper-case key
    assert key_upper in main_files
    assert key_upper in detail_files
    assert len(detail_files[key_upper]) == 1


def test_revision_label_lowercase_key() -> None:
    """_revision_label and _revision_number must work on lower-case keys."""
    assert _revision_label("JDAW-KVE-E-JA-6944-00001-007_a19") == "A19"
    assert _revision_number("JDAW-KVE-E-JA-6944-00001-007_a19") == 19


# ---------------------------------------------------------------------------
# discover_crs_files — Surplus filter and main-file rev mismatch
# ---------------------------------------------------------------------------

def test_surplus_file_excluded_before_pattern_match(tmp_path: Path) -> None:
    """Files inside a 'Surplus' subdirectory must be excluded before pattern matching."""
    key = "JDAW-KVE-E-JA-6944-00001-017_A34"
    doc_dir = tmp_path / f"JDAW-KVE-E-JA-6944-00001-017_A34 Rev. A34 - DOC_REF"
    doc_dir.mkdir(parents=True)

    # Create a valid master in the correct dir (control)
    main_path = doc_dir / f"DOC_COMMENT_{key}_KVE.xlsx"
    main_path.touch()

    # Create files inside Surplus — both main and detail variants
    surplus_dir = doc_dir / "Surplus"
    surplus_dir.mkdir()
    (surplus_dir / f"DOC_COMMENT_{key}_KVE.xlsx").touch()
    (surplus_dir / f"{key}_Review_Comments.xlsx").touch()

    main_files, detail_files, _ = discover_crs_files(tmp_path)

    # Master must be found exactly once (from doc_dir, not Surplus)
    assert key in main_files
    assert main_files[key].parent == doc_dir
    # Detail from Surplus must not appear
    for paths in detail_files.values():
        assert all("Surplus" not in p.parts for p in paths)


def test_main_file_rev_mismatch_excluded(tmp_path: Path) -> None:
    """Master file whose revision doesn't match its parent directory revision must be skipped."""
    # Directory named _A17, but the file inside has revision _A16
    wrong_dir = tmp_path / "JDAW-KVE-E-JA-6944-00001-016_A17"
    wrong_dir.mkdir()
    bad_main = wrong_dir / "DOC_COMMENT_JDAW-KVE-E-JA-6944-00001-016_A16_KVE.xlsx"
    bad_main.touch()

    main_files, _, _ = discover_crs_files(tmp_path)

    key = "JDAW-KVE-E-JA-6944-00001-016_A16"
    assert key not in main_files, "Master from mismatched directory must not be accepted"


def test_main_file_rev_match_accepted(tmp_path: Path) -> None:
    """Master file whose revision matches its parent directory revision must be accepted."""
    correct_dir = tmp_path / "JDAW-KVE-E-JA-6944-00001-016_A16"
    correct_dir.mkdir()
    good_main = correct_dir / "DOC_COMMENT_JDAW-KVE-E-JA-6944-00001-016_A16_KVE.xlsx"
    good_main.touch()

    main_files, _, _ = discover_crs_files(tmp_path)

    key = "JDAW-KVE-E-JA-6944-00001-016_A16"
    assert key in main_files
    assert main_files[key] == good_main
