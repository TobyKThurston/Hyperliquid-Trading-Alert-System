"""FastAPI application entry point."""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.logging import configure_logging, get_logger
from api.config import settings
from api.routes import health, rules, alerts, candles
from api.middleware.auth import APIKeyMiddleware

# Configure logging
configure_logging(settings.log_level)
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Pulse - Hyperliquid Alerting Backend",
    description="Production-grade backend for Hyperliquid price alerts",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("api_starting", host=settings.api_host, port=settings.api_port)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("api_shutting_down")


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_config=None,
    )

