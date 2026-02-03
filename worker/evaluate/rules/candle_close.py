"""Candle close rule."""
from worker.evaluate.rules.base import BaseRule
from worker.ingest.hyperliquid import Candle
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional


class CandleCloseRule(BaseRule):
    """Rule that triggers when candle close meets condition."""

    async def evaluate(
        self, config: dict, candle: Candle, db: AsyncSession
    ) -> Optional[float]:
        """Check if candle close meets condition."""
        value = float(config["value"])
        operator = config["operator"]
        close_price = float(candle.close)

        if operator == ">=":
            if close_price >= value:
                return close_price
        elif operator == "<=":
            if close_price <= value:
                return close_price

        return None

