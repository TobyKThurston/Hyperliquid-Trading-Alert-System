"""API key authentication + rate limiting middleware.

Combines auth and rate-limit in one pass so ordering is explicit:
  1. Public paths (/health, /docs, etc.) bypass everything.
  2. Read-only verbs (GET/HEAD/OPTIONS) bypass auth.
  3. Write verbs require X-API-Key. Either the admin env-var key OR a
     DB-backed key (stored as SHA-256 hash) is accepted.
  4. Authenticated requests are rate-limited per key via Redis. If Redis
     is unavailable, requests are allowed (fail-open).

Raising HTTPException inside BaseHTTPMiddleware doesn't trigger Starlette's
exception handlers — we return JSONResponse directly instead.
"""

import hashlib
from collections.abc import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from api.config import settings
from api.ratelimit import check_rate_limit
from core.logging import get_logger
from core.time import utcnow
from db.base import AsyncSessionLocal
from db.models import ApiKey

logger = get_logger(__name__)

PUBLIC_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}
READ_METHODS = {"GET", "HEAD", "OPTIONS"}


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        if request.method in READ_METHODS:
            return await call_next(request)

        raw_key = request.headers.get("X-API-Key")
        if not raw_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing X-API-Key header"},
            )

        bucket_id: str
        limit: int

        if raw_key == settings.api_key:
            # Admin/legacy env-var key: no DB row, use configured ceiling.
            bucket_id = "admin"
            limit = settings.admin_rate_limit_per_minute
        else:
            key_hash = _hash_key(raw_key)
            try:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(ApiKey).where(
                            ApiKey.key_hash == key_hash,
                            ApiKey.is_active.is_(True),
                        )
                    )
                    api_key = result.scalar_one_or_none()
                    if api_key is None:
                        return JSONResponse(
                            status_code=401,
                            content={"detail": "Invalid or inactive API key"},
                        )
                    bucket_id = str(api_key.id)
                    limit = api_key.requests_per_minute
                    api_key.last_used_at = utcnow()
                    await db.commit()
            except Exception as e:
                logger.error("api_key_lookup_failed", error=str(e))
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Auth backend unavailable"},
                )

        rl = await check_rate_limit(settings.redis_url, bucket_id, limit)
        if not rl.allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(rl.reset_in),
                    "X-RateLimit-Limit": str(rl.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rl.reset_in),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rl.limit)
        response.headers["X-RateLimit-Remaining"] = str(rl.remaining)
        response.headers["X-RateLimit-Reset"] = str(rl.reset_in)
        return response
