"""Regression tests for worker.main.save_candle exception handling."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from worker.ingest.hyperliquid import Candle
from worker.main import save_candle


def _candle() -> Candle:
    return Candle(
        symbol="BTC",
        timestamp=datetime(2024, 1, 1, 0, 0, 0),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        interval_seconds=900,
    )


@pytest.mark.asyncio
async def test_save_candle_swallows_integrity_error():
    """Duplicate candles (unique constraint) must be silently skipped."""
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=IntegrityError("dup", None, Exception("dup")))
    db.rollback = AsyncMock()

    # Must not raise.
    await save_candle(db, _candle())

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_candle_propagates_non_integrity_error():
    """Connection drops, disk full, etc. must NOT be silently swallowed."""
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=OperationalError("connection lost", None, Exception("boom")))
    db.rollback = AsyncMock()

    with pytest.raises(OperationalError):
        await save_candle(db, _candle())
