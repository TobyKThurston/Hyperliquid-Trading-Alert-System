# Pulse - Hyperliquid Trading Alert System

[![CI](https://github.com/TobyKThurston/Hyperliquid-Trading-Alert-System/actions/workflows/ci.yml/badge.svg)](https://github.com/TobyKThurston/Hyperliquid-Trading-Alert-System/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Backend service for Hyperliquid price alerts. Polls market data, evaluates rules, and sends notifications via Discord webhooks.

Built for traders and developers who need reliable alerting without managing infrastructure.

## Features

- RESTful API with 9 endpoints
- 4 rule types (price threshold, percent move, candle close, MACD cross)
- Idempotent alert delivery with database-level deduplication
- Exponential backoff retry mechanism (max 5 attempts, 32s delay)
- Delivery attempt audit trail with latency tracking
- Health checks and metrics endpoints
- Comprehensive test suite (58+ tests)
- Docker Compose setup for local development
- CI/CD pipeline with GitHub Actions
- Structured JSON logging

## Tech Stack

- **API**: FastAPI, Pydantic v2
- **Database**: PostgreSQL 16, SQLAlchemy 2.0, Alembic
- **Worker**: Python 3.12, asyncio
- **Testing**: pytest, pytest-asyncio
- **Infrastructure**: Docker, Docker Compose
- **CI/CD**: GitHub Actions
- **Code Quality**: ruff

## Project Structure

```
hyperliquidalert/
├── api/              # FastAPI application
│   ├── routes/       # API endpoints
│   ├── models/       # Pydantic models
│   └── middleware/   # Auth middleware
├── worker/           # Background worker service
│   ├── ingest/       # Data ingestion
│   ├── evaluate/     # Rule evaluation engine
│   └── dispatch/     # Alert delivery
├── db/               # Database models and migrations
├── core/             # Shared utilities (logging, exceptions)
├── tests/            # Test suite (unit + integration)
├── docs/             # Documentation
└── docker-compose.yml
```

## How It Works

1. Worker polls Hyperliquid `/info` endpoint every 60 seconds
2. New candles are saved to PostgreSQL
3. Rules matching the candle symbol are evaluated
4. If a rule triggers, an alert is created (enforced idempotency)
5. Alert is dispatched via webhook, with retries on failure

See [docs/architecture.md](docs/architecture.md) for details.

## Quickstart

```bash
# 1. Clone and setup
git clone https://github.com/TobyKThurston/Hyperliquid-Trading-Alert-System.git
cd Hyperliquid-Trading-Alert-System
cp .env.example .env
# Edit .env with your API_KEY

# 2. Start services
docker-compose up -d

# 3. Verify health
curl http://localhost:8000/health

# 4. Check API docs
open http://localhost:8000/docs
```

Migrations run automatically on API startup. See [docs/local-dev.md](docs/local-dev.md) for detailed setup.

## API

Full API reference: [docs/api.md](docs/api.md)

**Create a rule:**
```bash
curl -X POST http://localhost:8000/api/v1/rules \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "BTC Alert",
    "rule_type": "price_threshold",
    "symbol": "BTC",
    "config": {"threshold": 50000, "operator": ">="},
    "discord_webhook_url": "https://discord.com/api/webhooks/..."
  }'
```

**List candles:**
```bash
curl "http://localhost:8000/api/v1/candles?symbol=BTC&limit=10"
```

**List alerts:**
```bash
curl "http://localhost:8000/api/v1/alerts?symbol=BTC&limit=20"
```

## Rules

### Price Threshold

Triggers when price crosses a threshold.

```json
{
  "rule_type": "price_threshold",
  "config": {
    "threshold": 50000,
    "operator": ">="
  },
  "cooldown_seconds": 3600
}
```

### Percent Move

Triggers when price moves by N% within T seconds.

```json
{
  "rule_type": "percent_move",
  "config": {
    "percent_threshold": 5.0,
    "window_seconds": 300
  }
}
```

### Candle Close

Triggers when candle close meets condition.

```json
{
  "rule_type": "candle_close",
  "config": {
    "value": 50000,
    "operator": ">="
  }
}
```

### MACD Cross

Triggers on MACD signal line crossover (requires 50+ candles).

```json
{
  "rule_type": "macd_cross",
  "config": {
    "fast_period": 12,
    "slow_period": 26,
    "signal_period": 9,
    "crossover_type": "bullish"
  }
}
```

See [docs/api.md](docs/api.md) for all rule types and detailed examples.

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=. --cov-report=term-missing

# Specific test file
pytest tests/integration/test_api_candles.py -v
```

## Observability

**Health endpoint:**
```bash
curl http://localhost:8000/health
```

**Metrics endpoint:**
```bash
curl http://localhost:8000/metrics
```

**Logs:**
- Structured JSON logs (structlog)
- Worker logs: `docker-compose logs -f worker`
- API logs: `docker-compose logs -f api`

See [docs/runbook.md](docs/runbook.md) for operations guide.

## Security

- Never commit `.env` files
- Webhook URLs contain authentication tokens - treat as secrets
- Rotate API keys if exposed
- See [SECURITY.md](SECURITY.md) for details

## Documentation

- [Architecture](docs/architecture.md) - System design and data flow
- [Local Development](docs/local-dev.md) - Setup and workflow
- [API Reference](docs/api.md) - Endpoints and examples
- [Runbook](docs/runbook.md) - Operations and troubleshooting
- [Troubleshooting](docs/troubleshooting.md) - Common issues and fixes

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Roadmap

- [ ] WebSocket support for real-time candle streaming
- [ ] Additional rule types (RSI, Bollinger Bands)
- [ ] Prometheus metrics export
- [ ] Rate limiting per API key
- [ ] Alert delivery webhook history API endpoint

## License

MIT License - see [LICENSE](LICENSE) for details.
