"""RSI threshold rule."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Candle as CandleModel
from worker.evaluate.indicators import calculate_rsi
from worker.evaluate.rules.base import BaseRule
from worker.ingest.hyperliquid import Candle


class RSIRule(BaseRule):
    """Triggers when RSI crosses into overbought/oversold territory.

    Config:
        period:    int, default 14
        threshold: float, RSI level that triggers the alert
        direction: 'overbought' — fires when RSI >= threshold (default 70)
                   'oversold'   — fires when RSI <= threshold (default 30)

    Only fires on the bar where RSI *crosses* the threshold, not on every
    bar that stays past it — avoids spammy alerts in extended trends.
    """

    async def evaluate(
        self, config: dict, candle: Candle, db: AsyncSession
    ) -> Optional[float]:
        period = int(config.get("period", 14))
        direction = config["direction"]
        if direction not in ("overbought", "oversold"):
            return None

        default_threshold = 70.0 if direction == "overbought" else 30.0
        threshold = float(config.get("threshold", default_threshold))

        lookback = max(period * 5, 100)
        result = await db.execute(
            select(CandleModel)
            .where(
                CandleModel.symbol == candle.symbol,
                CandleModel.interval_seconds == 900,
            )
            .order_by(CandleModel.timestamp.desc())
            .limit(lookback)
        )
        candles = result.scalars().all()

        if len(candles) <= period:
            return None

        prices = [float(c.close) for c in reversed(candles)]
        rsi_values = calculate_rsi(prices, period)
        if len(rsi_values) < 2:
            return None

        current = rsi_values[-1]
        previous = rsi_values[-2]

        if direction == "overbought":
            if previous < threshold <= current:
                return current
        else:
            if previous > threshold >= current:
                return current

        return None
