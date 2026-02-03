"""FastAPI dependencies."""
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from db.base import get_db_session
from api.config import settings
from typing import Optional


async def get_db() -> AsyncSession:
    """Dependency for database session."""
    async for session in get_db_session():
        yield session


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """Verify API key from header."""
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True

