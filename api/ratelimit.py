"""Redis-backed rate limiting.

Uses a fixed-window-per-minute counter: one INCR per request, EXPIRE set
on first hit. Simple and cheap — at most 2 round-trips. The fixed-window
edge-burst (up to 2x limit across a window boundary) is fine for this
use-case; we're protecting downstream webhooks, not enforcing billing.

If Redis is unreachable or disabled, we fail OPEN (log + allow). A
rate-limit outage should not take down the API.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from core.logging import get_logger

logger = get_logger(__name__)

_redis_client = None  # Lazy, module-level


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_in: int  # Seconds until the current window resets


async def _get_client(redis_url: str | None):
    """Return a cached redis.asyncio client, or None if disabled/unreachable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not redis_url:
        return None
    try:
        import redis.asyncio as redis_asyncio
    except ImportError:
        logger.warn("redis_package_missing_ratelimit_disabled")
        return None
    try:
        client = redis_asyncio.from_url(redis_url, decode_responses=True)
        await client.ping()
        _redis_client = client
        return client
    except Exception as e:
        logger.warn("redis_connect_failed_ratelimit_disabled", error=str(e))
        return None


async def check_rate_limit(
    redis_url: str | None,
    bucket_id: str,
    limit_per_minute: int,
) -> RateLimitResult:
    """Check the fixed-window bucket. Fails open on Redis errors."""
    client = await _get_client(redis_url)
    if client is None:
        return RateLimitResult(
            allowed=True, limit=limit_per_minute, remaining=limit_per_minute, reset_in=60
        )

    now = int(time.time())
    window = now // 60
    key = f"rl:{bucket_id}:{window}"
    reset_in = 60 - (now % 60)

    try:
        count = await client.incr(key)
        if count == 1:
            # First hit in this window — set TTL so bucket auto-cleans.
            await client.expire(key, 61)
    except Exception as e:
        logger.warn("redis_ratelimit_error_failing_open", error=str(e))
        return RateLimitResult(
            allowed=True, limit=limit_per_minute, remaining=limit_per_minute, reset_in=reset_in
        )

    remaining = max(0, limit_per_minute - count)
    return RateLimitResult(
        allowed=count <= limit_per_minute,
        limit=limit_per_minute,
        remaining=remaining,
        reset_in=reset_in,
    )


async def close_client() -> None:
    """Close the cached Redis client (used on app shutdown)."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
        _redis_client = None
