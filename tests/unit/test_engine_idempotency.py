"""Regression tests for the alert idempotency race."""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from db.models import Alert, Rule
from worker.evaluate.engine import RuleEvaluator
from worker.ingest.hyperliquid import Candle


async def _make_persisted_rule(db_session) -> Rule:
    rule = Rule(
        id=uuid.uuid4(),
        name="test rule",
        symbol="BTC",
        rule_type="price_threshold",
        config={"threshold": 50000, "operator": ">="},
        cooldown_seconds=0,
        is_active=True,
    )
    db_session.add(rule)
    await db_session.commit()
    return rule


@pytest.mark.asyncio
async def test_create_alert_returns_none_on_conflict(db_session):
    """Second _create_alert for the same (rule, window) returns None, not raise."""
    rule = await _make_persisted_rule(db_session)

    evaluator = RuleEvaluator(db_session)
    candle = Candle(
        symbol="BTC",
        timestamp=datetime(2024, 1, 1, 12, 30, 15),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
    )
    window_start, window_end = evaluator._get_idempotency_window(candle.timestamp)

    first = await evaluator._create_alert(rule, candle, window_start, window_end, 50500.0)
    assert first is not None

    second = await evaluator._create_alert(rule, candle, window_start, window_end, 50500.0)
    assert second is None


@pytest.mark.asyncio
async def test_evaluate_twice_produces_exactly_one_alert(db_session):
    """Back-to-back evaluate() calls in the same window yield one alert, no exception."""
    from sqlalchemy import select

    rule = await _make_persisted_rule(db_session)
    evaluator = RuleEvaluator(db_session)

    candle = Candle(
        symbol="BTC",
        timestamp=datetime(2024, 1, 1, 12, 30, 15),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
    )

    a1 = await evaluator.evaluate(rule, candle)
    a2 = await evaluator.evaluate(rule, candle)

    # Exactly one of the two returns a new alert; the other is suppressed.
    assert (a1 is None) ^ (a2 is None)

    result = await db_session.execute(select(Alert).where(Alert.rule_id == rule.id))
    rows = result.scalars().all()
    assert len(rows) == 1
