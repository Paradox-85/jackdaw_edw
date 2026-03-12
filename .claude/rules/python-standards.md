---
description: Python coding standards — linting, docstrings, patterns
---

# Python Standards

## Linting (pyproject.toml — enforced via pre-commit)
```toml
[tool.black]
line-length = 88
target-version = 'py311'

[tool.ruff]
select = ["E", "F", "W", "UP", "I", "C90"]
ignore = ["E501"]
max-complexity = 10

[tool.mypy]
strict = true
disallow_untyped_defs = true

[tool.pydocstyle]
convention = "google"

[tool.sqlfluff]
dialect = "postgresql"
line-length = 88
```
Setup: `pip install pre-commit && pre-commit install`

## Type Hints — mandatory on all functions
```python
async def sync_tags(
    session: AsyncSession,
    csv_path: str,
    batch_size: int = 500,
) -> dict[str, int]:
```

## Docstrings — Google style, mandatory on all public functions
```python
def calculate_row_hash(row: pd.Series) -> str:
    """
    Compute MD5 hash of a pandas Series for CDC comparison.

    Args:
        row: Series of string-coerced field values.

    Returns:
        Hex MD5 digest string.

    Example:
        >>> calculate_row_hash(pd.Series(["JDA-21-LIT-101", "Active"]))
        'a3f2c1...'
    """
```

## Comments: WHY not WHAT
```python
# CORRECT — explains reason, not action
# SCD2: skip DB write if hash unchanged — avoids redundant history records
if existing_hash == current_hash:
    stats["unchanged"] += 1
    continue

# WRONG — restates the code
# increment counter
stats["updated"] += 1
```

## Special comment formats
```python
# FIXED: NaT→None was inserting string 'NaT' into TIMESTAMP columns (2026-03-12)
# TODO: Add async Ollama enrichment pass [HIGH, Q2-2026, ~2d]
```

## Self-documenting code (priority over comments)
- Descriptive names: `sync_tags_with_scd2()` not `process()`
- Functions ≤ 50 lines, single responsibility
- No `process`, `handle`, `do_stuff` function names

## SQLAlchemy 2.x patterns
```python
# DML — always atomic
with engine.begin() as conn:
    conn.execute(text("INSERT INTO project_core.tag ..."), params)

# Read-only — connect() is sufficient
with engine.connect() as conn:
    df = pd.read_sql(text("SELECT ..."), conn)
```

## Pandas — mandatory read settings
```python
# Preserve literal "NA" strings from EIS source files
df = pd.read_excel(path, dtype=str, na_filter=False)
df = pd.read_csv(path, dtype=str, na_filter=False)
```

## clean_string — standard helper (always use for raw source values)
```python
def clean_string(value) -> str | None:
    """Return stripped string or None for empty/null/NaN values."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    result = str(value).strip()
    return result if result else None
```

## Date conversion
```python
def to_dt(value) -> datetime | None:
    """Convert source value to datetime or None — never raises."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return pd.to_datetime(value).to_pydatetime()
    except Exception:
        return None
```

## Prohibited
- `except Exception: pass` — always log and handle specifically
- `print()` inside flows/tasks — use `get_run_logger()`
- Bare `except:` without type
- `import *`
- Hardcoded DB credentials (always from `config/db_config.yaml`)
