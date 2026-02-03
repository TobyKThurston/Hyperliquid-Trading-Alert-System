"""API key authentication middleware."""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from api.config import settings
from typing import Callable


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to verify API key for write operations."""

    async def dispatch(self, request: Request, call_next: Callable) -> Callable:
        """Check API key for POST, PUT, DELETE requests."""
        # Skip auth for GET requests and health/metrics endpoints
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)
        
        if request.url.path in ("/health", "/metrics", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)
        
        # Check API key header
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != settings.api_key:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        
        return await call_next(request)

