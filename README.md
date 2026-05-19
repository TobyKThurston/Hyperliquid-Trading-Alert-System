# Pulse — Hyperliquid Trading Alert System

[![CI](https://github.com/TobyKThurston/Hyperliquid-Trading-Alert-System/actions/workflows/ci.yml/badge.svg)](https://github.com/TobyKThurston/Hyperliquid-Trading-Alert-System/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**A production-grade Python backend that streams live crypto market data, evaluates user-defined trading rules, and delivers alerts reliably — with exactly-once guarantees, automatic retries, and a full audit trail.**

Streams Hyperliquid market data over WebSocket, evaluates six types of technical-analysis rules, and delivers alerts via Discord and generic webhooks — backed by database-level idempotency, exponential-backoff retry, and per-attempt delivery auditing.

> 💡 **For reviewers:** this is a portfolio project built to show how production trading infrastructure is actually engineered — durability, exactly-once delivery semantics, observability, and testing — not just "if price > X, send a message." Skim **[What This Project Demonstrates](#what-this-project-demonstrates)** for a 30-second overview.

**Tech at a glance:** Python 3.12 · FastAPI · async SQLAlchemy 2.0 · PostgreSQL · Redis · asyncio worker · Docker · GitHub Actions CI · 46 automated tests

---

## What This Project Demonstrates

A quick map of the engineering competencies this codebase shows in practice:

| Competency | Where it shows up |
| ---------- | ----------------- |
| **Backend API design** | 10-endpoint REST API with FastAPI, Pydantic v2 validation, and auto-generated OpenAPI docs |
| **Distributed-systems thinking** | Exactly-once delivery via a Postgres unique constraint — correct even with concurrent workers |
| **Resilience & fault tolerance** | Exponential-backoff retries, crash-safe retry state, WebSocket auto-reconnect with gap-backfill, fail-open rate limiting |
| **Async programming** | Full `asyncio` worker pipeline (ingest → evaluate → dispatch) and async SQLAlchemy throughout |
| **Data engineering** | Streaming market-data ingestion, OHLCV storage, and technical indicators (RSI, MACD, Bollinger Bands) computed from scratch |
| **Security** | SHA-256-hashed API keys, secret handling, per-key rate limiting |
| **Testing & CI** | 46 unit + integration tests, in-memory SQLite, automated lint + test on every push |
| **Operational maturity** | Structured JSON logging, health/metrics endpoints, Docker Compose, migrations, runbook docs |

---

## Highlights

- **6 rule types** — price threshold, percent move, candle close, MACD crossover, RSI bands, Bollinger band touch/break
- **Exactly-once alerting** — Postgres unique constraint on `(rule_id, window_start, window_end)` makes duplicate alerts impossible even with concurrent workers
- **Resilient delivery** — exponential backoff (max 5 attempts, capped at 32s), background retry scheduler, per-attempt latency + response-code audit trail
- **Two ingest modes** — primary WebSocket stream with auto-reconnect and REST gap-backfill, plus a REST-poll fallback for rollback
- **Auth + rate limiting** — SHA-256 hashed DB-backed API keys (raw key shown once at creation) plus Redis fixed-window rate limiting that fails open on outage
- **10 REST endpoints** with OpenAPI docs at `/docs`
- **46 tests passing** — unit + integration, in-memory SQLite, zero deprecation warnings on Python 3.13

## Tech Stack

| Layer            | Tech                                                  |
| ---------------- | ----------------------------------------------------- |
| API              | FastAPI, Pydantic v2, async SQLAlchemy 2.0            |
| Database         | PostgreSQL 16, Alembic migrations                     |
| Cache / limiter  | Redis 7                                               |
| Worker           | Python 3.12+ asyncio, `websockets`, `httpx`           |
| Testing          | pytest, pytest-asyncio, aiosqlite                     |
| Infrastructure   | Docker Compose, GitHub Actions                        |
| Observability    | structlog (JSON logs), `/metrics` endpoint            |

## Architecture

```
                                  ┌────────────────────────────┐
   Hyperliquid WS  ─────────►     │  worker (asyncio)          │
       (live candles)              │                            │
                                  │  ingest → evaluate → dispatch
                                  │     │        │         │
       Hyperliquid REST  ◄────────┤  (gap-      (rule      (Discord +
       (gap-backfill / fallback)   │   backfill)  registry)  generic webhook)
                                  └─────┬─────────────┬──────────┘
                                        │             │
                                        ▼             ▼
                                  ┌──────────┐   ┌──────────┐
                                  │ Postgres │   │ Redis    │
                                  │ candles  │   │ ratelim  │
                                  │ rules    │   └────▲─────┘
                                  │ alerts   │        │
                                  │ attempts │        │
                                  │ api_keys │        │
                                  └────▲─────┘        │
                                       │              │
                                  ┌────┴──────────────┴──────┐
                                  │ FastAPI                  │
                                  │ (CRUD rules, list alerts │
                                  │  + delivery attempts,    │
                                  │  query candles)          │
                                  └──────────────────────────┘
```

See [`docs/architecture.md`](docs/architecture.md) for the long version.

## Project Structure

```
hyperliquidalert/
├── api/                # FastAPI service
│   ├── routes/         # Endpoint handlers
│   ├── models/         # Pydantic request/response models
│   ├── middleware/     # API key auth + rate-limit hop
│   └── ratelimit.py    # Redis fixed-window limiter
├── worker/             # Async worker service
│   ├── ingest/         # Hyperliquid WS + REST client
│   ├── evaluate/       # Rule registry + indicators (RSI, MACD, BB)
│   └── dispatch/       # Webhook senders + retry scheduler
├── db/                 # SQLAlchemy models + Alembic migrations
├── core/               # Cross-cutting helpers (logging, time, exceptions)
├── tests/              # unit + integration suites
├── scripts/            # Operational scripts (e.g. create_api_key.py)
├── docs/               # Architecture, runbook, API reference
└── docker-compose.yml
```

## Quickstart

```bash
git clone https://github.com/TobyKThurston/Hyperliquid-Trading-Alert-System.git
cd Hyperliquid-Trading-Alert-System
cp .env.example .env          # set API_KEY (admin) and any overrides

docker-compose up -d           # postgres + redis + api + worker
curl http://localhost:8000/health
open http://localhost:8000/docs
```

Migrations run automatically on API startup (`entrypoint_api.sh`). See [`docs/local-dev.md`](docs/local-dev.md) for the full setup.

## Authentication & Rate Limiting

Two ways to authenticate write requests via the `X-API-Key` header:

1. **Admin key** — value of the `API_KEY` env var. Bypasses the DB lookup and uses a higher rate-limit ceiling (`ADMIN_RATE_LIMIT_PER_MINUTE`, default 1000/min). For development and operational scripts.
2. **DB-backed keys** — created with `scripts/create_api_key.py`, stored as SHA-256 hashes. The raw key is printed exactly once and discarded; a leaked DB dump can't be replayed.

```bash
docker-compose exec api python scripts/create_api_key.py "prod-dashboard" --rpm 120
# id:   3c1f...
# key:  pk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Save the key now — it cannot be retrieved later.
```

Read endpoints (`GET`/`HEAD`/`OPTIONS`) and the public paths (`/health`, `/metrics`, `/docs`, `/openapi.json`, `/redoc`) skip auth. Authenticated requests are rate-limited per key in Redis. If Redis is unreachable, the limiter **fails open** — a rate-limit outage doesn't take down the API.

## API

10 endpoints. Full reference: [`docs/api.md`](docs/api.md).

| Method | Path                                  | Purpose                                    |
| ------ | ------------------------------------- | ------------------------------------------ |
| GET    | `/health`                             | Liveness probe                             |
| GET    | `/metrics`                            | Active rules, pending alerts, db status    |
| POST   | `/api/v1/rules`                       | Create a rule (validated per `rule_type`)  |
| GET    | `/api/v1/rules`                       | List rules                                 |
| GET    | `/api/v1/rules/{rule_id}`             | Get one rule                               |
| PUT    | `/api/v1/rules/{rule_id}`             | Update a rule                              |
| DELETE | `/api/v1/rules/{rule_id}`             | Delete a rule                              |
| GET    | `/api/v1/alerts`                      | List alerts (filter by rule/symbol)        |
| GET    | `/api/v1/alerts/{alert_id}/deliveries`| Per-attempt delivery audit trail           |
| GET    | `/api/v1/candles`                     | Query stored OHLCV candles                 |

Example — create a rule:

```bash
curl -X POST http://localhost:8000/api/v1/rules \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "BTC breakout",
    "rule_type": "price_threshold",
    "symbol": "BTC",
    "config": {"threshold": 50000, "operator": ">="},
    "discord_webhook_url": "https://discord.com/api/webhooks/...",
    "cooldown_seconds": 3600
  }'
```

## Rule Types

All rules accept `cooldown_seconds` (suppress re-fires) and either / both of `discord_webhook_url`, `generic_webhook_url`.

### Price threshold
```json
{ "rule_type": "price_threshold",
  "config": { "threshold": 50000, "operator": ">=" } }
```

### Percent move
Triggers when price moves `percent_threshold` % within `window_seconds`.
```json
{ "rule_type": "percent_move",
  "config": { "percent_threshold": 5.0, "window_seconds": 300 } }
```

### Candle close
Triggers when the closing price of the latest candle meets the condition.
```json
{ "rule_type": "candle_close",
  "config": { "value": 50000, "operator": ">=" } }
```

### MACD crossover
Bullish or bearish signal-line cross. Requires ~50+ candles of history.
```json
{ "rule_type": "macd_cross",
  "config": { "fast_period": 12, "slow_period": 26,
              "signal_period": 9, "crossover_type": "bullish" } }
```

### RSI bands
Fires only on the bar where RSI **crosses** the threshold (no spam during extended trends).
```json
{ "rule_type": "rsi",
  "config": { "period": 14, "threshold": 70, "direction": "overbought" } }
```

### Bollinger Bands
`event: "touch"` fires on the transition bar; `event: "break"` fires while close is beyond the band.
```json
{ "rule_type": "bollinger_bands",
  "config": { "period": 20, "std_dev": 2.0, "band": "upper", "event": "break" } }
```

## Reliability Design

A few decisions worth calling out — these are why the system holds up under load and partial failure:

- **Idempotency at the database**, not the application. The `uq_alert_window` unique constraint on `(rule_id, window_start, window_end)` serializes concurrent inserts. Two workers seeing the same trigger in the same minute → one alert, no advisory locks needed.
- **Retry state lives on the alert row.** `delivery_status`, `delivery_attempts`, and `last_delivery_attempt` let the retry scheduler resume work after a crash without losing track of in-flight attempts.
- **Per-attempt audit trail** in `alert_delivery_attempts` (status, response code, latency_ms, error). Surface-able via `GET /alerts/{id}/deliveries`.
- **WebSocket gap-backfill.** Reconnects don't lose candles — on every WS reconnect the worker REST-fetches anything closed between the last seen timestamp and the new connection.
- **Naive-UTC by convention** through `core/time.utcnow()` — all timestamps are produced through one helper, sidestepping `datetime.utcnow()` deprecation and `fromtimestamp()` returning local time.

## Testing

```bash
pytest                                # 46 tests, ~0.4s
pytest --cov=. --cov-report=term-missing
pytest tests/integration/test_api_candles.py -v
```

CI runs the full suite plus `ruff check` on every push (see `.github/workflows/ci.yml`).

## Observability

- **Structured JSON logs** via structlog — every request, every rule eval, every webhook attempt.
- `GET /health` — liveness check.
- `GET /metrics` — active rules count, pending-alerts count, DB connectivity.
- Logs: `docker-compose logs -f worker` / `docker-compose logs -f api`.

See [`docs/runbook.md`](docs/runbook.md) for ops procedures.

## Security

- Never commit `.env` files (gitignored).
- Webhook URLs contain authentication tokens — treat as secrets.
- API keys are hashed at rest. The raw key is shown exactly once at creation.
- Admin key (`API_KEY` env var) bypasses the DB and should be rotated if exposed.
- See [`SECURITY.md`](SECURITY.md).

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — system design and data flow
- [`docs/api.md`](docs/api.md) — full API reference
- [`docs/local-dev.md`](docs/local-dev.md) — setup and workflow
- [`docs/runbook.md`](docs/runbook.md) — ops and on-call
- [`docs/troubleshooting.md`](docs/troubleshooting.md) — common issues

## Roadmap

- [ ] Prometheus metrics export (`prometheus-fastapi-instrumentator` is wired in but custom metrics not yet exposed)
- [ ] Token-bucket rate limiting (currently fixed-window-per-minute)
- [ ] Alert delivery retry policy as configuration (currently 5 attempts, 32s cap)
- [ ] gRPC streaming endpoint for low-latency alert consumption

## Contributing

Contributions welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT — see [`LICENSE`](LICENSE).
