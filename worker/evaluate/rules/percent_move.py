"""Percent move rule."""
from worker.evaluate.rules.base import BaseRule
from worker.ingest.hyperliquid import Candle
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from typing import Optional
from db.models import Candle as CandleModel


class PercentMoveRule(BaseRule):
    """Rule that triggers on percent move within a time window."""

    async def evaluate(
        self, config: dict, candle: Candle, db: AsyncSession
    ) -> Optional[float]:
        """Check if percent move exceeds threshold."""
        percent_threshold = float(config["percent_threshold"])
        window_seconds = int(config["window_seconds"])

        # Find oldest candle in window
        start_time = candle.timestamp - timedelta(seconds=window_seconds)
        result = await db.execute(
            select(CandleModel)
            .where(
                CandleModel.symbol == candle.symbol,
                CandleModel.timestamp >= start_time,
            )
            .order_by(CandleModel.timestamp.asc())
            .limit(1)
        )
        old_candle = result.scalar_one_or_none()

        if not old_candle:
            return None

        # Calculate percent change
        old_price = float(old_candle.close)
        new_price = float(candle.close)
        percent_change = abs(((new_price - old_price) / old_price) * 100)

        if percent_change >= percent_threshold:
            return new_price

        return None

