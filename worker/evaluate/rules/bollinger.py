"""Bollinger Bands rule."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Candle as CandleModel
from worker.evaluate.indicators import calculate_bollinger_bands
from worker.evaluate.rules.base import BaseRule
from worker.ingest.hyperliquid import Candle


class BollingerBandsRule(BaseRule):
    """Triggers on Bollinger-band interactions.

    Config:
        period:   int, default 20
        std_dev:  float, default 2.0
        band:     'upper' | 'lower'
        event:    'touch'  — price crosses the band on this bar
                  'break'  — close is beyond the band (above upper / below lower)

    Fires only on the transition bar ('touch') or while the break condition
    holds ('break') — callers use cooldown_seconds to throttle.
    """

    async def evaluate(self, config: dict, candle: Candle, db: AsyncSession) -> float | None:
        period = int(config.get("period", 20))
        std_dev = float(config.get("std_dev", 2.0))
        band = config["band"]
        event = config["event"]

        if band not in ("upper", "lower") or event not in ("touch", "break"):
            return None

        lookback = max(period * 3, 60)
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

        if len(candles) < period + 1:
            return None

        prices = [float(c.close) for c in reversed(candles)]
        upper, _middle, lower = calculate_bollinger_bands(prices, period, std_dev)
        if len(upper) < 2:
            return None

        current_close = float(candle.close)
        prev_close = prices[-2]

        if band == "upper":
            band_now = upper[-1]
            band_prev = upper[-2]
            if event == "break":
                if current_close > band_now:
                    return current_close
            else:  # touch
                if prev_close <= band_prev and current_close >= band_now:
                    return current_close
        else:  # lower band
            band_now = lower[-1]
            band_prev = lower[-2]
            if event == "break":
                if current_close < band_now:
                    return current_close
            else:  # touch
                if prev_close >= band_prev and current_close <= band_now:
                    return current_close

        return None
