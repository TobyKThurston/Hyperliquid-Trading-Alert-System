"""Technical indicators."""

import math


def calculate_ema(prices: list[float], period: int) -> list[float]:
    """Calculate Exponential Moving Average."""
    if len(prices) < period:
        return []

    multiplier = 2.0 / (period + 1)
    ema_values = []

    # Start with SMA
    sma = sum(prices[:period]) / period
    ema_values.append(sma)

    # Calculate EMA for remaining values
    for price in prices[period:]:
        ema = (price - ema_values[-1]) * multiplier + ema_values[-1]
        ema_values.append(ema)

    return ema_values


def calculate_macd(
    prices: list[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
) -> tuple[list[float], list[float], list[float]]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Returns:
        (macd_line, signal_line, histogram)
    """
    if len(prices) < slow_period + signal_period:
        return [], [], []

    # Calculate EMAs
    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)

    if len(fast_ema) < slow_period or len(slow_ema) == 0:
        return [], [], []

    # MACD line = fast EMA - slow EMA
    # Align lengths
    min_len = min(len(fast_ema), len(slow_ema))
    fast_ema_aligned = fast_ema[-min_len:]
    slow_ema_aligned = slow_ema[-min_len:]

    macd_line = [f - s for f, s in zip(fast_ema_aligned, slow_ema_aligned)]

    if len(macd_line) < signal_period:
        return [], [], []

    # Signal line = EMA of MACD line
    signal_line = calculate_ema(macd_line, signal_period)

    # Histogram = MACD line - Signal line
    if len(signal_line) == 0:
        return [], [], []

    # Align lengths
    min_len = min(len(macd_line), len(signal_line))
    macd_aligned = macd_line[-min_len:]
    signal_aligned = signal_line[-min_len:]

    histogram = [m - s for m, s in zip(macd_aligned, signal_aligned)]

    return macd_line, signal_line, histogram


def calculate_rsi(prices: list[float], period: int = 14) -> list[float]:
    """Wilder's Relative Strength Index.

    Returns a list of RSI values aligned to the tail of `prices`. First
    RSI value corresponds to index `period` in `prices`. Returns an empty
    list when there's insufficient data.
    """
    if len(prices) <= period:
        return []

    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rsi_values: list[float] = []
    rsi_values.append(_rsi_from_avgs(avg_gain, avg_loss))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rsi_values.append(_rsi_from_avgs(avg_gain, avg_loss))

    return rsi_values


def _rsi_from_avgs(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calculate_bollinger_bands(
    prices: list[float], period: int = 20, std_dev: float = 2.0
) -> tuple[list[float], list[float], list[float]]:
    """Bollinger Bands.

    Returns (upper, middle, lower) — each a list aligned to the tail of
    `prices`. First value corresponds to index `period - 1`. Middle band
    is the simple moving average; upper/lower are `std_dev` population
    standard deviations away.
    """
    if len(prices) < period or period <= 0:
        return [], [], []

    upper: list[float] = []
    middle: list[float] = []
    lower: list[float] = []

    for i in range(period - 1, len(prices)):
        window = prices[i - period + 1 : i + 1]
        mean = sum(window) / period
        variance = sum((p - mean) ** 2 for p in window) / period
        sd = math.sqrt(variance)
        middle.append(mean)
        upper.append(mean + std_dev * sd)
        lower.append(mean - std_dev * sd)

    return upper, middle, lower
