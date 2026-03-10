## 3️⃣ Prefect ETL Flows (prefect_flows.md)

```markdown
---
name: Prefect ETL Flows
description: Async Prefect 3.0 patterns for EDW orchestration
tags: [prefect, etl, async, orchestration, python]
trigger_keywords: ["flow", "prefect", "task", "orchestrate"]
---

# Prefect 3.0 ETL Patterns

## Flow Structure (Extract → Transform → Load)

```python
from prefect import flow, task
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import logging

logger = logging.getLogger(__name__)

@task(name="extract-tags", retries=2, retry_delay_seconds=30)
async def extract_tags(file_path: str) -> list[dict]:
    """
    Extract tags from CSV source.
    
    Args:
        file_path: Path to CSV (use symlink data/current/tags.csv).
    
    Returns:
        Raw records as list of dicts.
    
    Raises:
        FileNotFoundError: If CSV missing.
    """
    import pandas as pd
    
    df = pd.read_csv(file_path, dtype=str, na_filter=False)
    logger.info(f"Extracted {len(df)} tags")
    return df.to_dict(orient='records')


@task(name="transform-tags")
async def transform_tags(raw_tags: list[dict]) -> list[dict]:
    """Transform: hash, validate, deduplicate."""
    import hashlib
    
    transformed = []
    for tag in raw_tags:
        # Why hash: SCD2 change detection (avoid full table scan)
        row_hash = hashlib.md5(
            f"{tag['tag_code']}|{tag['tag_name']}".encode()
        ).hexdigest()
        tag['row_hash'] = row_hash
        transformed.append(tag)
    
    logger.info(f"Transformed {len(transformed)} tags")
    return transformed


@task(name="load-tags")
async def load_tags(
    session: AsyncSession,
    transformed_tags: list[dict]
) -> dict[str, int]:
    """
    Load tags with SCD Type 2.
    
    Returns:
        dict: {'inserted': N, 'updated': N}
    """
    # Implementation: MERGE query or ORM operations
    # See scd2.md skill for full example
    pass


@flow(name="tag-sync", description="Sync tags from CSV to PostgreSQL")
async def sync_tag_flow(config_path: str = "config/settings.yaml"):
    """
    Master flow: Extract → Transform → Load.
    
    Args:
        config_path: Path to settings.yaml.
    """
    from etl.tasks.common import load_config
    
    config = load_config(config_path)
    engine = create_async_engine(config['database']['async_url'])
    
    try:
        # Extract
        raw_tags = await extract_tags(
            f"{config['paths']['current_dir']}/tags.csv"
        )
        
        # Transform
        transformed = await transform_tags(raw_tags)
        
        # Load
        async with engine.begin() as conn:
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy.ext.asyncio import AsyncSession as AS
            
            session_factory = sessionmaker(engine, class_=AS)
            async with session_factory() as session:
                result = await load_tags(session, transformed)
        
        logger.info(f"Flow completed: {result}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    import asyncio
    asyncio.run(sync_tag_flow())
```

## Key Patterns

1. **Async/Await**: All tasks must be async
2. **Error Handling**: Retries, logging, audit trail
3. **Atomicity**: session.begin() for transactions
4. **Batch Size**: 500-1000 rows per transaction
5. **Logging**: Always log to audit_core and local logs

## Task Naming Convention
- `extract-*`: Load raw data
- `transform-*`: Data cleaning, validation, hashing
- `load-*`: UPSERT to database
- `resolve-*`: Post-processing (e.g., hierarchy resolution)

## Flow Scheduling
```python
from prefect.schedules import CronSchedule

sync_tag_flow.schedule = CronSchedule(cron="0 2 * * *")  # Daily at 02:00 UTC
```
```

---