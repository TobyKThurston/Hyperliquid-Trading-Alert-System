"""Technical indicators."""
from typing import List
from decimal import Decimal


def calculate_ema(prices: List[float], period: int) -> List[float]:
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
    prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
) -> tuple[List[float], List[float], List[float]]:
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

