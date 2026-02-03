"""Rule evaluation engine."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Optional
from db.models import Rule, Alert
from worker.ingest.hyperliquid import Candle
from worker.evaluate.rules import (
    PriceThresholdRule,
    PercentMoveRule,
    CandleCloseRule,
    MACDCrossRule,
)
from core.logging import get_logger
from core.exceptions import InvalidRuleConfigError

logger = get_logger(__name__)


class RuleEvaluator:
    """Evaluates rules against candles and creates alerts.

    Handles cooldown periods and idempotency windows to prevent duplicate alerts.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_classes = {
            "price_threshold": PriceThresholdRule(),
            "percent_move": PercentMoveRule(),
            "candle_close": CandleCloseRule(),
            "macd_cross": MACDCrossRule(),
        }

    def _get_idempotency_window(self, timestamp: datetime) -> tuple[datetime, datetime]:
        """Get 1-minute idempotency window for timestamp."""
        window_start = timestamp.replace(second=0, microsecond=0)
        window_end = window_start + timedelta(minutes=1)
        return (window_start, window_end)

    async def _is_in_cooldown(self, rule: Rule, symbol: str) -> bool:
        """Check if rule is in cooldown period."""
        if rule.cooldown_seconds == 0:
            return False

        result = await self.db.execute(
            select(Alert)
            .where(Alert.rule_id == rule.id, Alert.symbol == symbol.upper())
            .order_by(Alert.triggered_at.desc())
            .limit(1)
        )
        last_alert = result.scalar_one_or_none()

        if not last_alert:
            return False

        cooldown_end = last_alert.triggered_at + timedelta(seconds=rule.cooldown_seconds)
        return datetime.utcnow() < cooldown_end

    async def _alert_exists(
        self, rule_id: str, window_start: datetime, window_end: datetime
    ) -> bool:
        """Check if alert already exists for this idempotency window."""
        result = await self.db.execute(
            select(Alert).where(
                Alert.rule_id == rule_id,
                Alert.window_start == window_start,
                Alert.window_end == window_end,
            )
        )
        return result.scalar_one_or_none() is not None

    async def _create_alert(
        self,
        rule: Rule,
        candle: Candle,
        window_start: datetime,
        window_end: datetime,
        trigger_value: float,
    ) -> Alert:
        """Create alert record in database."""
        alert = Alert(
            rule_id=rule.id,
            symbol=candle.symbol,
            rule_type=rule.rule_type,
            triggered_at=candle.timestamp,
            trigger_value=trigger_value,
            window_start=window_start,
            window_end=window_end,
            delivery_status="pending",
        )
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def evaluate(self, rule: Rule, candle: Candle) -> Optional[Alert]:
        """Evaluate rule against candle.

        Returns Alert if triggered, None otherwise. Enforces cooldown and idempotency.
        """
        if await self._is_in_cooldown(rule, candle.symbol):
            return None

        window_start, window_end = self._get_idempotency_window(candle.timestamp)
        if await self._alert_exists(rule.id, window_start, window_end):
            return None

        rule_class = self.rule_classes.get(rule.rule_type)
        if not rule_class:
            logger.error("unknown_rule_type", rule_type=rule.rule_type, rule_id=str(rule.id))
            return None

        try:
            trigger_value = await rule_class.evaluate(rule.config, candle, self.db)

            if trigger_value is not None:
                alert = await self._create_alert(
                    rule, candle, window_start, window_end, trigger_value
                )
                logger.info(
                    "alert_triggered",
                    rule_id=str(rule.id),
                    symbol=candle.symbol,
                    trigger_value=trigger_value,
                )
                return alert

            return None
        except Exception as e:
            logger.error(
                "rule_evaluation_failed",
                rule_id=str(rule.id),
                symbol=candle.symbol,
                error=str(e),
                exc_info=True,
            )
            return None

