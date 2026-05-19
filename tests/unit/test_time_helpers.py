"""Unit tests for core.time helpers."""

from datetime import UTC, datetime

from core.time import from_ms, now_ms, to_ms, utcnow


def test_utcnow_is_naive():
    dt = utcnow()
    assert dt.tzinfo is None


def test_utcnow_matches_wall_clock_utc_within_2s():
    before = datetime.now(UTC).replace(tzinfo=None)
    dt = utcnow()
    after = datetime.now(UTC).replace(tzinfo=None)
    assert before <= dt <= after


def test_from_ms_is_tz_independent():
    # 2024-01-01T00:00:00Z
    ms = 1_704_067_200_000
    dt = from_ms(ms)
    assert dt.tzinfo is None
    assert dt == datetime(2024, 1, 1, 0, 0, 0)


def test_to_ms_roundtrip():
    ms = 1_704_067_200_123
    assert to_ms(from_ms(ms)) == ms


def test_now_ms_matches_from_ms_roundtrip():
    ms = now_ms()
    dt = from_ms(ms)
    assert abs(to_ms(dt) - ms) < 1000
