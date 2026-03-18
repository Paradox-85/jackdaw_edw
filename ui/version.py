"""
ui/version.py — Build metadata for Jackdaw EDW Control Center.

VERSION is bumped manually on each release.
GIT_HASH and BUILD_DATE are read from the git repo at import time.
"""
from __future__ import annotations
import subprocess
from datetime import timezone

__version__ = "0.2.0"


def _git(args: list[str]) -> str:
    """Run a git command and return stdout, or empty string on failure."""
    try:
        return subprocess.check_output(
            ["git"] + args,
            stderr=subprocess.DEVNULL,
            cwd=__file__,          # resolved to repo root by git
        ).decode().strip()
    except Exception:
        return ""


# Short commit hash (7 chars)
GIT_HASH: str = _git(["rev-parse", "--short", "HEAD"]) or "unknown"

# Commit date in UTC — ISO format → "2026-03-18 13:03"
_raw_date = _git(["log", "-1", "--format=%cd", "--date=format:%Y-%m-%d %H:%M"])
BUILD_DATE: str = _raw_date or "unknown"


def version_string() -> str:
    """Return formatted version string for display."""
    return f"v{__version__} · git:{GIT_HASH} · {BUILD_DATE} UTC"
