"""
Task template for EDW.
Location: etl/tasks/your_task.py
References: sql/schema/, config/settings.yaml
"""
from prefect import task
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


@task(
    name="task-name",
    tags=["edw", "sync", "your-domain"],
    retries=2,
    retry_delay_seconds=30
)
async def your_task(
    session: AsyncSession,
    param_one: str,
    param_two: Optional[int] = None
) -> dict[str, Any]:
    """
    Task description.
    
    Args:
        session: AsyncSession for DB operations
        param_one: Description
        param_two: Optional parameter
        
    Returns:
        dict: {success: bool, count: int, errors: list}
        
    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If DB operation fails
        
    References:
        - sql/schema/: Check table structure
        - config/settings.yaml: Load configs if needed
    """
    result = {
        "success": True,
        "count": 0,
        "errors": []
    }
    
    try:
        # TODO: Implement task logic
        async with session.begin():
            pass
        
        return result
    except Exception as e:
        logger.error(f"Task failed: {str(e)}", exc_info=True)
        result['success'] = False
        result['errors'].append(str(e))
        raise