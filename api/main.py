"""FastAPI application entry point."""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.middleware.auth import APIKeyMiddleware
from api.ratelimit import close_client
from api.routes import alerts, candles, health, rules
from core.logging import configure_logging, get_logger

# Configure logging
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("api_starting", host=settings.api_host, port=settings.api_port)
    try:
        yield
    finally:
        await close_client()
        logger.info("api_shutting_down")


# Create FastAPI app
app = FastAPI(
    title="Pulse - Hyperliquid Alerting Backend",
    description="Production-grade backend for Hyperliquid price alerts",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware. Wildcard origins with allow_credentials=True is
# rejected by browsers, so we always use an explicit allowlist (comma-
# separated via CORS_ORIGINS env var).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add API key middleware
app.add_middleware(APIKeyMiddleware)

# Include routers
app.include_router(health.router)
app.include_router(rules.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(candles.router, prefix="/api/v1")


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_config=None,
    )
