"""
Prefect 3.0 Flow template for EDW.
Location: etl/flows/your_flow.py
References: sql/schema/, config/settings.yaml
"""
from prefect import flow, task
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from typing import Any, Optional
import logging
import yaml

logger = logging.getLogger(__name__)


def load_config(path: str = "config/settings.yaml") -> dict:
    """Load configuration from YAML."""
    with open(path, 'r') as f:
        return yaml.safe_load(f)


@task(retries=2, retry_delay_seconds=30, name="extract-data")
async def extract_data(
    session: AsyncSession, 
    source_file: str,
    dtype: Optional[dict] = None
) -> list[dict]:
    """
    Extract data from source (CSV/DB).
    
    Args:
        session: AsyncSession for database queries
        source_file: Path to source (use symlink from data/)
        dtype: Pandas dtype mapping
        
    Returns:
        list[dict]: Extracted records
        
    Raises:
        FileNotFoundError: If source_file not found
        SQLAlchemyError: If DB query fails
    """
    import pandas as pd
    
    try:
        # Read from symlink: data/current/ or data/_history/
        df = pd.read_csv(source_file, dtype=str, na_filter=False)
        return df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Extract failed for {source_file}: {str(e)}", exc_info=True)
        raise


@task(name="transform-data")
async def transform_data(raw_data: list[dict]) -> list[dict]:
    """
    Transform data according to business rules.
    
    - Hash comparison for UPSERT
    - SCD Type 2 compliance
    - Preserve _raw columns
    - FK resolution with fallback
    """
    import hashlib
    
    transformed = []
    for row in raw_data:
        # Generate row hash
        row_str = '|'.join(f"{k}:{v}" for k, v in sorted(row.items()))
        row_hash = hashlib.md5(row_str.encode()).hexdigest()
        
        row['row_hash'] = row_hash
        transformed.append(row)
    
    return transformed


@task(name="load-data")
async def load_data(
    session: AsyncSession, 
    transformed_data: list[dict],
    target_table: str
) -> dict[str, Any]:
    """
    Load to target table with SCD Type 2 tracking.
    
    Args:
        session: AsyncSession
        transformed_data: Data to load
        target_table: Full table name (e.g., project_core.tag)
        
    Returns:
        dict: {inserted: int, updated: int, errors: list}
    """
    result = {"inserted": 0, "updated": 0, "errors": []}
    
    async with session.begin():
        for row in transformed_data:
            try:
                # TODO: Implement UPSERT logic
                # Check if exists by hash
                # Insert new or Update existing
                # Log to _history table if changed
                pass
            except Exception as e:
                logger.error(f"Load error for row {row}: {str(e)}")
                result['errors'].append(str(e))
    
    return result


@flow(
    name="edw-sync",
    description="Master sync flow for EDW",
    version="1.0"
)
async def main_flow(config_path: str = "config/settings.yaml"):
    """
    Main orchestration: Extract → Transform → Load
    
    References: sql/schema/, sql/migrations/
    """
    config = load_config(config_path)
    
    # Create DB engine from config
    engine = create_async_engine(config['database']['async_url'])
    
    async with engine.begin() as conn:
        # Extract
        raw_data = await extract_data(
            conn,
            source_file=f"{config['paths']['current_dir']}/tags.csv"
        )
        logger.info(f"Extracted {len(raw_data)} records")
        
        # Transform
        transformed = await transform_data(raw_data)
        
        # Load
        result = await load_data(
            conn,
            transformed_data=transformed,
            target_table="project_core.tag"
        )
        logger.info(f"Load result: {result}")
    
    await engine.dispose()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main_flow())