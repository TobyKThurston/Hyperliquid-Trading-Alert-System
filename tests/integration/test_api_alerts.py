"""Integration tests for alerts API."""

from decimal import Decimal

import pytest

from core.time import utcnow
from db.models import Alert, Rule


@pytest.mark.asyncio
async def test_list_alerts(test_client, db_session):
    """Test listing alerts."""
    # Create test rule and alert
    rule = Rule(
        name="Test Rule",
        rule_type="price_threshold",
        symbol="BTC",
        config={"threshold": 50000, "operator": ">="},
    )
    db_session.add(rule)
    await db_session.commit()

    alert = Alert(
        rule_id=rule.id,
        symbol="BTC",
        rule_type="price_threshold",
        triggered_at=utcnow(),
        trigger_value=Decimal("50100"),
        window_start=utcnow().replace(second=0, microsecond=0),
        window_end=utcnow().replace(second=0, microsecond=0),
        delivery_status="delivered",
    )
    db_session.add(alert)
    await db_session.commit()

    response = await test_client.get("/api/v1/alerts")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["alerts"]) >= 1


@pytest.mark.asyncio
async def test_list_alerts_filter_by_rule(test_client, db_session):
    """Test listing alerts filtered by rule_id."""
    # Create test rules and alerts
    rule1 = Rule(
        name="Rule 1",
        rule_type="price_threshold",
        symbol="BTC",
        config={"threshold": 50000, "operator": ">="},
    )
    rule2 = Rule(
        name="Rule 2",
        rule_type="price_threshold",
        symbol="ETH",
        config={"threshold": 3000, "operator": ">="},
    )
    db_session.add(rule1)
    db_session.add(rule2)
    await db_session.commit()

    alert1 = Alert(
        rule_id=rule1.id,
        symbol="BTC",
        rule_type="price_threshold",
        triggered_at=utcnow(),
        trigger_value=Decimal("50100"),
        window_start=utcnow().replace(second=0, microsecond=0),
        window_end=utcnow().replace(second=0, microsecond=0),
        delivery_status="delivered",
    )
    alert2 = Alert(
        rule_id=rule2.id,
        symbol="ETH",
        rule_type="price_threshold",
        triggered_at=utcnow(),
        trigger_value=Decimal("3100"),
        window_start=utcnow().replace(second=0, microsecond=0),
        window_end=utcnow().replace(second=0, microsecond=0),
        delivery_status="delivered",
    )
    db_session.add(alert1)
    db_session.add(alert2)
    await db_session.commit()

    response = await test_client.get(f"/api/v1/alerts?rule_id={rule1.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["alerts"][0]["rule_id"] == str(rule1.id)
