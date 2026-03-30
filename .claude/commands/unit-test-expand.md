Systematically expand test coverage for: $ARGUMENTS

## Phase 1 — Coverage analysis (READ ONLY)

```bash
# Run existing tests and get coverage report
python -m pytest $ARGUMENTS --cov=$ARGUMENTS --cov-report=term-missing -v 2>/dev/null \
  || echo "No tests found yet — will create from scratch"
```

Identify untested:

1. **Happy path variants** — different input combinations
2. **SCD2 branches** — hash match (No Changes), hash mismatch (Updated), new record (New), absent record (Deleted)
3. **FK resolution paths** — found, miss (None returned), empty string input
4. **Error paths** — DB connection failure, malformed CSV row, encoding error
5. **Boundary conditions** — empty DataFrame, single row, 100k+ rows (performance)
6. **Audit paths** — does tag_status_history get written? does sync_run_stats get written?

## Phase 2 — Generate tests using Red-Green-Refactor

For each gap found:

1. Write the FAILING test first (Red) — run it to confirm it fails
2. Confirm it fails for the RIGHT reason (not syntax error)
3. Implement minimum code to make it pass (Green)
4. Refactor if needed

Test naming convention:
```python
def test_<function>_<scenario>_<expected_outcome>():
    # e.g.:
    # test_sync_tags_hash_unchanged_skips_db_write
    # test_resolve_fk_on_miss_returns_none_and_logs_warning
    # test_calculate_row_hash_empty_values_returns_consistent_hash
```

## Phase 3 — EDW-specific test fixtures

Always use these fixtures for ETL tests:

```python
@pytest.fixture
def sample_tag_row():
    return pd.Series({
        "TAG_NAME": "JDA-21-LIT-101",
        "TAG_CLASS_NAME": "Instrument",
        "AREA_CODE": "21",
        "STATUS": "Active"
    })

@pytest.fixture
def empty_lookup():
    return {}  # simulate FK miss scenario

@pytest.fixture
def populated_lookup():
    return {"Instrument": uuid.uuid4(), "Electrical": uuid.uuid4()}
```

## Phase 4 — Verify improvement

```bash
python -m pytest $ARGUMENTS --cov=$ARGUMENTS --cov-report=term-missing -v
```

Report: coverage before → coverage after, new tests added, remaining gaps.
