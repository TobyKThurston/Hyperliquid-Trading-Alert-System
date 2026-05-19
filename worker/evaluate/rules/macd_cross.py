"""MACD crossover rule."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Candle as CandleModel
from worker.evaluate.indicators import calculate_macd
from worker.evaluate.rules.base import BaseRule
from worker.ingest.hyperliquid import Candle


class MACDCrossRule(BaseRule):
    """Rule that triggers on MACD signal line crossover."""

    async def evaluate(self, config: dict, candle: Candle, db: AsyncSession) -> float | None:
        """Check for MACD crossover."""
        fast_period = int(config.get("fast_period", 12))
        slow_period = int(config.get("slow_period", 26))
        signal_period = int(config.get("signal_period", 9))
        crossover_type = config["crossover_type"]

        # Fetch last 50 candles (need enough for MACD)
        result = await db.execute(
            select(CandleModel)
            .where(
                CandleModel.symbol == candle.symbol,
                CandleModel.interval_seconds == 900,  # 15m
            )
            .order_by(CandleModel.timestamp.desc())
            .limit(50)
        )
        candles = result.scalars().all()

        if len(candles) < slow_period + signal_period:
            return None

        # Extract close prices in chronological order
        prices = [float(c.close) for c in reversed(candles)]

        # Calculate MACD
        macd_line, signal_line, _ = calculate_macd(prices, fast_period, slow_period, signal_period)

        if len(macd_line) < 2 or len(signal_line) < 2:
            return None

        # Check for crossover
        macd_current = macd_line[-1]
        macd_previous = macd_line[-2]
        signal_current = signal_line[-1]
        signal_previous = signal_line[-2]

        if crossover_type == "bullish":
            # Bullish: MACD crosses above signal
            if macd_current > signal_current and macd_previous <= signal_previous:
                return float(candle.close)
        elif crossover_type == "bearish":
            # Bearish: MACD crosses below signal
            if macd_current < signal_current and macd_previous >= signal_previous:
                return float(candle.close)

        return None
