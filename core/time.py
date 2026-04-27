"""UTC time helpers.

Legacy DB columns in this project are naive `DateTime`. To stay compatible,
these helpers produce naive datetimes whose values represent UTC by
convention — the same model the existing columns already assume. Using
these helpers replaces two bug-prone stdlib calls:

* `datetime.utcnow()` — works but deprecated in 3.12+ and returns naive.
* `datetime.fromtimestamp(x)` — returns *local* time, not UTC (the bug).

All producers should route through `utcnow()` and `from_ms()`.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current time as naive UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def from_ms(ms: int) -> datetime:
    """Convert Unix epoch milliseconds to naive UTC."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).replace(tzinfo=None)


def now_ms() -> int:
    """Current Unix epoch time in milliseconds (timezone-safe)."""
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def to_ms(dt: datetime) -> int:
    """Convert a naive-UTC-by-convention datetime to Unix epoch milliseconds."""
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
