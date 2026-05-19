"""Price threshold rule."""

from sqlalchemy.ext.asyncio import AsyncSession

from worker.evaluate.rules.base import BaseRule
from worker.ingest.hyperliquid import Candle


class PriceThresholdRule(BaseRule):
    """Rule that triggers when price crosses a threshold."""

    async def evaluate(self, config: dict, candle: Candle, db: AsyncSession) -> float | None:
        """Check if price crosses threshold."""
        threshold = float(config["threshold"])
        operator = config["operator"]
        current_price = float(candle.close)

        if operator == ">=":
            if current_price >= threshold:
                return current_price
        elif operator == "<=":
            if current_price <= threshold:
                return current_price

        return None
