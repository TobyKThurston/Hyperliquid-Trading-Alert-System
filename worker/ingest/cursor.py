"""Cursor persistence for worker state."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from db.models import WorkerCursor
from worker.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


async def get_cursor(db: AsyncSession, symbol: str) -> WorkerCursor | None:
    """Get cursor for a symbol."""
    result = await db.execute(
        select(WorkerCursor).where(
            WorkerCursor.worker_id == settings.worker_id,
            WorkerCursor.symbol == symbol.upper(),
        )
    )
    return result.scalar_one_or_none()


async def update_cursor(db: AsyncSession, symbol: str, timestamp: datetime) -> None:
    """Update or create cursor for a symbol."""
    cursor = await get_cursor(db, symbol)
    
    if cursor:
        cursor.last_processed_timestamp = timestamp
        cursor.updated_at = datetime.utcnow()
    else:
        cursor = WorkerCursor(
            worker_id=settings.worker_id,
            symbol=symbol.upper(),
            last_processed_timestamp=timestamp,
        )
        db.add(cursor)
    
    await db.commit()


async def get_all_cursors(db: AsyncSession) -> dict[str, datetime]:
    """Get all cursors for this worker."""
    result = await db.execute(
        select(WorkerCursor).where(WorkerCursor.worker_id == settings.worker_id)
    )
    cursors = result.scalars().all()
    return {cursor.symbol: cursor.last_processed_timestamp for cursor in cursors}

