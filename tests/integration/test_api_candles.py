"""Integration tests for candles API."""

from datetime import timedelta
from decimal import Decimal

import pytest

from core.time import utcnow
from db.models import Candle


@pytest.mark.asyncio
async def test_get_candles_empty_returns_empty_list_total_0(test_client):
    """Test listing candles when DB is empty returns empty list."""
    response = await test_client.get("/api/v1/candles?symbol=BTC")

    assert response.status_code == 200
    data = response.json()
    assert data["candles"] == []
    assert data["total"] == 0
    assert data["limit"] == 200
    assert data["offset"] == 0
    assert data["order"] == "desc"


@pytest.mark.asyncio
async def test_get_candles_requires_symbol(test_client):
    """Test that symbol parameter is required."""
    response = await test_client.get("/api/v1/candles")

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_candles_filters_by_symbol_interval(test_client, db_session):
    """Test filtering candles by symbol and interval."""
    # Create candles with different symbols and intervals
    now = utcnow()

    candle1 = Candle(
        symbol="BTC",
        timestamp=now,
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("1000"),
        interval_seconds=900,
    )

    candle2 = Candle(
        symbol="ETH",
        timestamp=now,
        open=Decimal("3000"),
        high=Decimal("3100"),
        low=Decimal("2900"),
        close=Decimal("3050"),
        volume=Decimal("500"),
        interval_seconds=900,
    )

    candle3 = Candle(
        symbol="BTC",
        timestamp=now + timedelta(minutes=15),
        open=Decimal("50500"),
        high=Decimal("51500"),
        low=Decimal("49500"),
        close=Decimal("51000"),
        volume=Decimal("1100"),
        interval_seconds=1800,  # Different interval
    )

    db_session.add(candle1)
    db_session.add(candle2)
    db_session.add(candle3)
    await db_session.commit()

    # Filter by BTC and 900s interval
    response = await test_client.get("/api/v1/candles?symbol=BTC&interval_seconds=900")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["candles"]) == 1
    assert data["candles"][0]["symbol"] == "BTC"
    assert data["candles"][0]["interval_seconds"] == 900

    # Filter by ETH
    response = await test_client.get("/api/v1/candles?symbol=ETH")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["candles"][0]["symbol"] == "ETH"


@pytest.mark.asyncio
async def test_get_candles_respects_order_and_pagination(test_client, db_session):
    """Test ordering and pagination."""
    # Create multiple candles
    base_time = utcnow().replace(second=0, microsecond=0)
    candles = []

    for i in range(5):
        candle = Candle(
            symbol="BTC",
            timestamp=base_time + timedelta(minutes=15 * i),
            open=Decimal(f"{50000 + i * 100}"),
            high=Decimal(f"{51000 + i * 100}"),
            low=Decimal(f"{49000 + i * 100}"),
            close=Decimal(f"{50500 + i * 100}"),
            volume=Decimal("1000"),
            interval_seconds=900,
        )
        candles.append(candle)
        db_session.add(candle)

    await db_session.commit()

    # Test descending order (default)
    response = await test_client.get("/api/v1/candles?symbol=BTC&limit=3")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["candles"]) == 3
    assert data["order"] == "desc"
    # Most recent first
    assert float(data["candles"][0]["close"]) > float(data["candles"][1]["close"])

    # Test ascending order
    response = await test_client.get("/api/v1/candles?symbol=BTC&order=asc&limit=3")

    assert response.status_code == 200
    data = response.json()
    assert data["order"] == "asc"
    # Oldest first
    assert float(data["candles"][0]["close"]) < float(data["candles"][1]["close"])

    # Test pagination with offset
    response = await test_client.get("/api/v1/candles?symbol=BTC&limit=2&offset=2")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["candles"]) == 2
    assert data["offset"] == 2


@pytest.mark.asyncio
async def test_get_candles_time_range_filter(test_client, db_session):
    """Test filtering by time range."""
    base_time = utcnow().replace(second=0, microsecond=0)

    # Create candles at different times
    candle1 = Candle(
        symbol="BTC",
        timestamp=base_time - timedelta(hours=2),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("1000"),
        interval_seconds=900,
    )

    candle2 = Candle(
        symbol="BTC",
        timestamp=base_time - timedelta(hours=1),
        open=Decimal("50500"),
        high=Decimal("51500"),
        low=Decimal("49500"),
        close=Decimal("51000"),
        volume=Decimal("1100"),
        interval_seconds=900,
    )

    candle3 = Candle(
        symbol="BTC",
        timestamp=base_time,
        open=Decimal("51000"),
        high=Decimal("52000"),
        low=Decimal("50000"),
        close=Decimal("51500"),
        volume=Decimal("1200"),
        interval_seconds=900,
    )

    db_session.add(candle1)
    db_session.add(candle2)
    db_session.add(candle3)
    await db_session.commit()

    # Filter by start_time
    start_time = (base_time - timedelta(hours=1, minutes=30)).isoformat()
    response = await test_client.get(f"/api/v1/candles?symbol=BTC&start_time={start_time}")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2  # candle2 and candle3

    # Filter by end_time
    end_time = (base_time - timedelta(minutes=30)).isoformat()
    response = await test_client.get(f"/api/v1/candles?symbol=BTC&end_time={end_time}")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2  # candle1 and candle2

    # Filter by both start_time and end_time
    response = await test_client.get(
        f"/api/v1/candles?symbol=BTC&start_time={start_time}&end_time={end_time}"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1  # Only candle2
