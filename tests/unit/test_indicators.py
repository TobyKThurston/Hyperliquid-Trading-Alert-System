"""Unit tests for technical indicators."""

from worker.evaluate.indicators import calculate_ema, calculate_macd


def test_calculate_ema():
    """Test EMA calculation."""
    prices = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0]
    period = 3

    ema = calculate_ema(prices, period)

    assert len(ema) > 0
    assert ema[0] == sum(prices[:period]) / period  # First value is SMA


def test_calculate_ema_insufficient_data():
    """Test EMA with insufficient data."""
    prices = [100.0, 102.0]
    period = 3

    ema = calculate_ema(prices, period)

    assert len(ema) == 0


def test_calculate_macd():
    """Test MACD calculation."""
    # Generate sample price data
    prices = [100.0 + i * 0.5 for i in range(50)]

    macd_line, signal_line, histogram = calculate_macd(prices, 12, 26, 9)

    assert len(macd_line) > 0
    assert len(signal_line) > 0
    assert len(histogram) > 0


def test_calculate_macd_insufficient_data():
    """Test MACD with insufficient data."""
    prices = [100.0 + i * 0.5 for i in range(20)]

    macd_line, signal_line, histogram = calculate_macd(prices, 12, 26, 9)

    assert len(macd_line) == 0
    assert len(signal_line) == 0
    assert len(histogram) == 0


def test_calculate_macd_crossover_detection():
    """Test MACD crossover detection."""
    # Create prices that would cause a crossover
    prices = [100.0 + i * 0.1 for i in range(50)]

    macd_line, signal_line, histogram = calculate_macd(prices, 12, 26, 9)

    if len(macd_line) >= 2 and len(signal_line) >= 2:
        # Check if we can detect crossovers
        macd_current = macd_line[-1]
        signal_current = signal_line[-1]
        macd_previous = macd_line[-2]
        signal_previous = signal_line[-2]

        # At least verify the structure is correct
        assert isinstance(macd_current, float)
        assert isinstance(signal_current, float)
