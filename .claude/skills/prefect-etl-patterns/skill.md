---
name: prefect-etl-patterns
description: Prefect 3.0 flow/task patterns, deploy commands, error handling for EDW
---
# Prefect 3.0 — EDW Patterns

**Entry point:** `etl/flows/tag_sync.py:main_pipeline` (config: `config/default.yaml`)
**Tasks:** `etl/tasks/tag_sync.py` — `fetch_from_source`, `validate_schema`, `upsert_tags`

## Task template
```python
@task(name="fetch-raw-data", retries=2)
async def fetch_from_source(source_id: str) -> pd.DataFrame:
    logger = get_run_logger()
    try:
        df = pd.read_csv(path, dtype=str, na_filter=False)
        return df
    except Exception as e:
        logger.error(f"Fetch failed: {e}", exc_info=True)
        raise
```

## Flow order (mandatory)
```
fetch_from_source → validate_schema → upsert_tags → resolve_hierarchy → log_changes
```

## Commands
```bash
prefect server start
prefect deploy --entrypoint etl/flows/tag_sync.py:main_pipeline --name "tag-sync"
prefect flow-run ls
tail -f logs/prefect.log | grep ERROR
```
