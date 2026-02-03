# Architecture

## Overview

Pulse ingests market data from Hyperliquid, evaluates alert rules, and delivers notifications via webhooks.

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   FastAPI   │◄────►│  PostgreSQL  │◄────►│   Worker    │
│   Server    │      │   Database   │      │   Service   │
└─────────────┘      └──────────────┘      └──────┬──────┘
       │                                            │
       │                                            │
       │                                            ▼
       │                                    ┌──────────────┐
       │                                    │  Hyperliquid │
       │                                    │  REST API    │
       └────────────────────────────────────┴──────────────┘
                    Discord/Webhooks
```

## Components

**API Server** (`api/`)
- FastAPI app serving REST endpoints
- Manages rules and alert history
- Health checks and metrics

**Worker** (`worker/`)
- Polls Hyperliquid REST API for candles (60s interval)
- Evaluates rules against new candles
- Dispatches alerts via webhooks
- Retries failed deliveries with exponential backoff

**Database** (PostgreSQL)
- Stores rules, alerts, candles, delivery attempts
- Unique constraints prevent duplicate alerts
- Cursors track ingestion progress per symbol

## Data Flow

1. **Ingestion**: Worker polls Hyperliquid `/info` endpoint, fetches last 200 candles, yields new ones
2. **Storage**: Candles saved to DB with unique constraint `(symbol, timestamp, interval)`
3. **Evaluation**: For each candle, load matching rules, check cooldown/idempotency, evaluate
4. **Alert Creation**: If rule triggers, create alert with `(rule_id, window_start, window_end)` unique constraint
5. **Dispatch**: Send to Discord/generic webhook, record attempt in `alert_delivery_attempts`
6. **Retry**: Background task polls pending alerts, retries with backoff

## Design Decisions

**Polling vs WebSocket**: Hyperliquid WebSocket API is complex. Polling REST every 60s is simpler and reliable for 15m candles.

**Idempotency Windows**: 1-minute windows prevent duplicate alerts if worker restarts mid-evaluation. Unique constraint enforces at DB level.

**Detached Rule Objects**: Rules converted to dicts after loading to avoid SQLAlchemy lazy loading issues in async context.

