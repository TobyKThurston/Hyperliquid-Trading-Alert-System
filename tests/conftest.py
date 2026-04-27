"""Pytest configuration and fixtures."""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
import os

# Test database URL (in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="function")
async def db_session():
    """Create a test database session."""
    from db.base import Base
    # Ensure every model is registered on Base.metadata before create_all.
    # Without this import, tables only the FastAPI app ends up using (via the
    # integration tests) aren't declared yet when we build the schema.
    import db.models  # noqa: F401

    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestSessionLocal() as session:
        yield session
    
    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def test_client(db_session):
    """Create a test client."""
    from api.main import app
    from api.dependencies import get_db
    
    # Override get_db dependency
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def api_key():
    """Test API key."""
    return "test-api-key"


@pytest.fixture(autouse=True)
def set_test_env(api_key, monkeypatch):
    """Set test environment variables.

    `api.config.settings` is instantiated at import time — by the time
    fixtures run, it already holds whatever was in the real `.env`. Setting
    env vars alone is too late, so we also patch the cached Settings
    instance directly.
    """
    monkeypatch.setenv("API_KEY", api_key)
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    try:
        from api.config import settings as api_settings
        monkeypatch.setattr(api_settings, "api_key", api_key)
    except ImportError:
        pass

