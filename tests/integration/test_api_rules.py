"""Integration tests for rules API."""

import pytest


@pytest.mark.asyncio
async def test_create_rule(test_client, api_key):
    """Test creating a rule."""
    response = await test_client.post(
        "/api/v1/rules",
        json={
            "name": "BTC Price Alert",
            "rule_type": "price_threshold",
            "symbol": "BTC",
            "config": {"threshold": 50000, "operator": ">="},
            "cooldown_seconds": 3600,
        },
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "BTC Price Alert"
    assert data["rule_type"] == "price_threshold"
    assert data["symbol"] == "BTC"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_rule_missing_api_key(test_client):
    """Test creating a rule without API key."""
    response = await test_client.post(
        "/api/v1/rules",
        json={
            "name": "BTC Price Alert",
            "rule_type": "price_threshold",
            "symbol": "BTC",
            "config": {"threshold": 50000, "operator": ">="},
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_rules(test_client, db_session, api_key):
    """Test listing rules."""
    from db.models import Rule

    # Create test rule
    rule = Rule(
        name="Test Rule",
        rule_type="price_threshold",
        symbol="BTC",
        config={"threshold": 50000, "operator": ">="},
    )
    db_session.add(rule)
    await db_session.commit()

    response = await test_client.get("/api/v1/rules")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["rules"]) >= 1


@pytest.mark.asyncio
async def test_get_rule(test_client, db_session, api_key):
    """Test getting a specific rule."""
    from db.models import Rule

    rule = Rule(
        name="Test Rule",
        rule_type="price_threshold",
        symbol="BTC",
        config={"threshold": 50000, "operator": ">="},
    )
    db_session.add(rule)
    await db_session.commit()
    rule_id = rule.id

    response = await test_client.get(f"/api/v1/rules/{rule_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(rule_id)
    assert data["name"] == "Test Rule"


@pytest.mark.asyncio
async def test_update_rule(test_client, db_session, api_key):
    """Test updating a rule."""
    from db.models import Rule

    rule = Rule(
        name="Test Rule",
        rule_type="price_threshold",
        symbol="BTC",
        config={"threshold": 50000, "operator": ">="},
    )
    db_session.add(rule)
    await db_session.commit()
    rule_id = rule.id

    response = await test_client.put(
        f"/api/v1/rules/{rule_id}",
        json={"name": "Updated Rule", "is_active": False},
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Rule"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_delete_rule(test_client, db_session, api_key):
    """Test deleting a rule."""
    from db.models import Rule

    rule = Rule(
        name="Test Rule",
        rule_type="price_threshold",
        symbol="BTC",
        config={"threshold": 50000, "operator": ">="},
    )
    db_session.add(rule)
    await db_session.commit()
    rule_id = rule.id

    response = await test_client.delete(
        f"/api/v1/rules/{rule_id}",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 204

    # Verify deleted
    get_response = await test_client.get(f"/api/v1/rules/{rule_id}")
    assert get_response.status_code == 404
