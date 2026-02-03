"""SQLAlchemy base configuration."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
import os


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Get database URL from environment or API/Worker settings
# Try to import from settings if available, otherwise use env var
try:
    from api.config import settings as api_settings
    DATABASE_URL = api_settings.database_url
except ImportError:
    try:
        from worker.config import settings as worker_settings
        DATABASE_URL = worker_settings.database_url
    except ImportError:
        DATABASE_URL = os.getenv(
            "DATABASE_URL", "postgresql+asyncpg://pulse_user:pulse_password@localhost:5432/pulse_db"
        )

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

