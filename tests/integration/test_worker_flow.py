"""Integration tests for worker flow."""

from datetime import timedelta
from decimal import Decimal

import pytest

from core.time import utcnow
from db.models import Alert, Rule
from worker.evaluate.engine import RuleEvaluator
from worker.ingest.hyperliquid import Candle


@pytest.mark.asyncio
async def test_rule_evaluator_cooldown(db_session):
    """Test rule evaluator respects cooldown."""
    # Create rule with cooldown
    rule = Rule(
        name="Test Rule",
        rule_type="price_threshold",
        symbol="BTC",
        config={"threshold": 50000, "operator": ">="},
        cooldown_seconds=3600,
    )
    db_session.add(rule)
    await db_session.commit()

    # Create recent alert (within cooldown)
    recent_alert = Alert(
        rule_id=rule.id,
        symbol="BTC",
        rule_type="price_threshold",
        triggered_at=utcnow() - timedelta(minutes=30),
        trigger_value=Decimal("50100"),
        window_start=utcnow() - timedelta(minutes=30),
        window_end=utcnow() - timedelta(minutes=30),
        delivery_status="delivered",
    )
    db_session.add(recent_alert)
    await db_session.commit()

    # Create candle that would trigger
    candle = Candle(
        symbol="BTC",
        timestamp=utcnow(),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
    )

    evaluator = RuleEvaluator(db_session)
    result = await evaluator.evaluate(rule, candle)

    # Should be None due to cooldown
    assert result is None


@pytest.mark.asyncio
async def test_rule_evaluator_idempotency(db_session):
    """Test rule evaluator prevents duplicate alerts."""
    rule = Rule(
        name="Test Rule",
        rule_type="price_threshold",
        symbol="BTC",
        config={"threshold": 50000, "operator": ">="},
    )
    db_session.add(rule)
    await db_session.commit()

    # Create existing alert for same window
    window_start = utcnow().replace(second=0, microsecond=0)
    window_end = window_start + timedelta(minutes=1)

    existing_alert = Alert(
        rule_id=rule.id,
        symbol="BTC",
        rule_type="price_threshold",
        triggered_at=utcnow(),
        trigger_value=Decimal("50100"),
        window_start=window_start,
        window_end=window_end,
        delivery_status="delivered",
    )
    db_session.add(existing_alert)
    await db_session.commit()

    # Create candle in same window
    candle = Candle(
        symbol="BTC",
        timestamp=window_start + timedelta(seconds=30),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
    )

    evaluator = RuleEvaluator(db_session)
    result = await evaluator.evaluate(rule, candle)

    # Should be None due to idempotency
    assert result is None
