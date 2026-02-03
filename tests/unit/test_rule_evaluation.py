"""Unit tests for rule evaluation."""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from worker.ingest.hyperliquid import Candle
from worker.evaluate.rules.price_threshold import PriceThresholdRule
from worker.evaluate.rules.percent_move import PercentMoveRule
from worker.evaluate.rules.candle_close import CandleCloseRule
from worker.evaluate.rules.macd_cross import MACDCrossRule


@pytest.mark.asyncio
async def test_price_threshold_above(db_session):
    """Test price threshold rule with >= operator."""
    rule = PriceThresholdRule()
    candle = Candle(
        symbol="BTC",
        timestamp=datetime.utcnow(),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
    )
    
    config = {"threshold": 50000, "operator": ">="}
    result = await rule.evaluate(config, candle, db_session)
    
    assert result == 50500.0


@pytest.mark.asyncio
async def test_price_threshold_below(db_session):
    """Test price threshold rule with <= operator."""
    rule = PriceThresholdRule()
    candle = Candle(
        symbol="BTC",
        timestamp=datetime.utcnow(),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("49000"),
    )
    
    config = {"threshold": 50000, "operator": "<="}
    result = await rule.evaluate(config, candle, db_session)
    
    assert result == 49000.0


@pytest.mark.asyncio
async def test_price_threshold_no_match(db_session):
    """Test price threshold rule when condition not met."""
    rule = PriceThresholdRule()
    candle = Candle(
        symbol="BTC",
        timestamp=datetime.utcnow(),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("49000"),
    )
    
    config = {"threshold": 50000, "operator": ">="}
    result = await rule.evaluate(config, candle, db_session)
    
    assert result is None


@pytest.mark.asyncio
async def test_candle_close_above(db_session):
    """Test candle close rule with >= operator."""
    rule = CandleCloseRule()
    candle = Candle(
        symbol="BTC",
        timestamp=datetime.utcnow(),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
    )
    
    config = {"value": 50000, "operator": ">="}
    result = await rule.evaluate(config, candle, db_session)
    
    assert result == 50500.0


@pytest.mark.asyncio
async def test_percent_move_rule(db_session):
    """Test percent move rule."""
    from db.models import Candle as CandleModel
    
    rule = PercentMoveRule()
    
    # Create old candle
    old_time = datetime.utcnow() - timedelta(minutes=10)
    old_candle_db = CandleModel(
        symbol="BTC",
        timestamp=old_time,
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50000"),
        interval_seconds=900,
    )
    db_session.add(old_candle_db)
    await db_session.commit()
    
    # Create new candle with 10% move
    new_candle = Candle(
        symbol="BTC",
        timestamp=datetime.utcnow(),
        open=Decimal("55000"),
        high=Decimal("56000"),
        low=Decimal("54000"),
        close=Decimal("55000"),
    )
    
    config = {"percent_threshold": 5.0, "window_seconds": 600}
    result = await rule.evaluate(config, new_candle, db_session)
    
    assert result == 55000.0

