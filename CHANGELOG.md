# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-XX

### Added
- REST API for managing alert rules (CRUD operations)
- Four rule types: price threshold, percent move, candle close, MACD crossover
- Candle ingestion from Hyperliquid REST API (15-minute intervals)
- Idempotent alert delivery with database-level deduplication
- Retry mechanism with exponential backoff (max 5 attempts, 32s max delay)
- Discord and generic webhook notifications
- Delivery attempt audit trail with latency and response code tracking
- Health checks and metrics endpoints
- Comprehensive test suite (58+ tests covering unit and integration scenarios)
- Docker Compose setup for local development
- CI/CD pipeline with GitHub Actions (linting, formatting, tests)
- Structured JSON logging with structlog
- Database migrations with Alembic
- Cursor-based ingestion tracking for graceful recovery
- Comprehensive documentation (architecture, API reference, runbook, troubleshooting)

### Technical Details
- FastAPI with async/await throughout
- PostgreSQL 16 with SQLAlchemy 2.0
- Python 3.12+
- 5 database tables with 6 indexes and 3 unique constraints
- 9 REST API endpoints
- 60-second polling interval for market data
- 200-candle rolling window per API request

