"""Unit tests for RSI and Bollinger Bands indicators."""
import math

from worker.evaluate.indicators import calculate_bollinger_bands, calculate_rsi


def test_rsi_all_gains_returns_100():
    """Strictly increasing prices have zero losses → RSI = 100."""
    prices = [100.0 + i for i in range(20)]
    rsi = calculate_rsi(prices, period=14)
    assert len(rsi) > 0
    for v in rsi:
        assert v == 100.0


def test_rsi_all_losses_returns_zero():
    """Strictly decreasing prices have zero gains → RSI = 0."""
    prices = [100.0 - i for i in range(20)]
    rsi = calculate_rsi(prices, period=14)
    assert len(rsi) > 0
    for v in rsi:
        assert v == 0.0


def test_rsi_insufficient_data_returns_empty():
    assert calculate_rsi([1.0, 2.0, 3.0], period=14) == []


def test_rsi_bounded():
    """RSI must always be in [0, 100] for any input."""
    prices = [100.0, 102.0, 101.0, 103.0, 99.0, 105.0, 97.0, 110.0, 92.0, 115.0, 90.0, 120.0, 88.0, 125.0, 85.0, 130.0]
    rsi = calculate_rsi(prices, period=7)
    assert len(rsi) > 0
    for v in rsi:
        assert 0.0 <= v <= 100.0


def test_bollinger_bands_centered_on_sma():
    """Middle band equals the simple moving average of the window."""
    prices = [10.0] * 30
    upper, middle, lower = calculate_bollinger_bands(prices, period=20, std_dev=2.0)
    assert len(middle) == 11
    # Constant series: sd=0 so upper == middle == lower == 10
    for u, m, low in zip(upper, middle, lower):
        assert u == 10.0
        assert m == 10.0
        assert low == 10.0


def test_bollinger_bands_known_values():
    """Spot-check a simple series we can compute by hand."""
    prices = [1.0, 2.0, 3.0, 4.0, 5.0]
    upper, middle, lower = calculate_bollinger_bands(prices, period=5, std_dev=1.0)
    assert len(middle) == 1
    mean = sum(prices) / 5
    variance = sum((p - mean) ** 2 for p in prices) / 5
    sd = math.sqrt(variance)
    assert middle[0] == mean
    assert math.isclose(upper[0], mean + sd)
    assert math.isclose(lower[0], mean - sd)


def test_bollinger_bands_insufficient_data():
    assert calculate_bollinger_bands([1.0, 2.0], period=20, std_dev=2.0) == ([], [], [])
