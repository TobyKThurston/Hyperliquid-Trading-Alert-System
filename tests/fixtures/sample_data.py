"""Sample data fixtures."""
from datetime import datetime, timedelta
from decimal import Decimal
from db.models import Rule, Alert, Candle


def create_sample_rule():
    """Create a sample rule."""
    return Rule(
        name="BTC Price Alert",
        rule_type="price_threshold",
        symbol="BTC",
        config={"threshold": 50000, "operator": ">="},
        cooldown_seconds=3600,
        is_active=True,
    )


def create_sample_alert(rule_id):
    """Create a sample alert."""
    now = datetime.utcnow()
    return Alert(
        rule_id=rule_id,
        symbol="BTC",
        rule_type="price_threshold",
        triggered_at=now,
        trigger_value=Decimal("50100"),
        window_start=now.replace(second=0, microsecond=0),
        window_end=now.replace(second=0, microsecond=0) + timedelta(minutes=1),
        delivery_status="pending",
    )


def create_sample_candle():
    """Create a sample candle."""
    return Candle(
        symbol="BTC",
        timestamp=datetime.utcnow(),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("1000"),
        interval_seconds=900,
    )

