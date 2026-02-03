# API Reference

Base URL: `http://localhost:8000`

## Authentication

Write endpoints (POST, PUT, DELETE) require API key:

```bash
curl -H "X-API-Key: your-api-key" ...
```

Read endpoints (GET) do not require authentication.

## Endpoints

### Health

#### GET /health

Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### GET /metrics

Basic metrics.

**Response:**
```json
{
  "rules_active": 5,
  "alerts_pending_delivery": 2,
  "database_status": "connected"
}
```

### Rules

#### POST /api/v1/rules

Create a new alert rule.

**Headers:**
- `X-API-Key: <key>` (required)
- `Content-Type: application/json`

**Request:**
```json
{
  "name": "BTC Price Alert",
  "rule_type": "price_threshold",
  "symbol": "BTC",
  "config": {
    "threshold": 50000,
    "operator": ">="
  },
  "cooldown_seconds": 3600,
  "discord_webhook_url": "https://discord.com/api/webhooks/...",
  "is_active": true
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "name": "BTC Price Alert",
  "rule_type": "price_threshold",
  "symbol": "BTC",
  "config": {...},
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/rules \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "BTC Alert",
    "rule_type": "price_threshold",
    "symbol": "BTC",
    "config": {"threshold": 50000, "operator": ">="}
  }'
```

#### GET /api/v1/rules

List rules with optional filters.

**Query Parameters:**
- `symbol` (string, optional): Filter by symbol
- `is_active` (boolean, optional): Filter by active status
- `limit` (int, default 50, max 100): Page size
- `offset` (int, default 0): Pagination offset

**Response:**
```json
{
  "rules": [...],
  "total": 10
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/rules?symbol=BTC&is_active=true&limit=10"
```

#### GET /api/v1/rules/{rule_id}

Get a specific rule.

**Response:** `200 OK` with rule object, or `404 Not Found`

#### PUT /api/v1/rules/{rule_id}

Update a rule (partial update supported).

**Headers:**
- `X-API-Key: <key>` (required)

**Request:** Any subset of rule fields

**Response:** `200 OK` with updated rule

#### DELETE /api/v1/rules/{rule_id}

Delete a rule.

**Headers:**
- `X-API-Key: <key>` (required)

**Response:** `204 No Content`

### Candles

#### GET /api/v1/candles

List candles with filters.

**Query Parameters:**
- `symbol` (string, **required**): Symbol (e.g., "BTC", "ETH")
- `interval_seconds` (int, default 900): Candle interval in seconds
- `start_time` (datetime, optional): Start time (ISO8601)
- `end_time` (datetime, optional): End time (ISO8601)
- `limit` (int, default 200, max 500): Maximum candles to return
- `offset` (int, default 0, max 100000): Pagination offset
- `order` (string, default "desc"): Sort order ("asc" or "desc")

**Response:**
```json
{
  "candles": [
    {
      "id": "uuid",
      "symbol": "BTC",
      "timestamp": "2024-01-01T12:00:00Z",
      "open": "50000",
      "high": "51000",
      "low": "49000",
      "close": "50500",
      "volume": "1000",
      "interval_seconds": 900
    }
  ],
  "total": 100,
  "limit": 200,
  "offset": 0,
  "order": "desc"
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/candles?symbol=BTC&limit=10&order=desc"
```

### Alerts

#### GET /api/v1/alerts

List alerts with optional filters.

**Query Parameters:**
- `rule_id` (UUID, optional): Filter by rule ID
- `symbol` (string, optional): Filter by symbol
- `limit` (int, default 50, max 100): Page size
- `offset` (int, default 0): Pagination offset

**Response:**
```json
{
  "alerts": [
    {
      "id": "uuid",
      "rule_id": "uuid",
      "symbol": "BTC",
      "rule_type": "price_threshold",
      "triggered_at": "2024-01-01T12:00:00Z",
      "trigger_value": "50100",
      "delivery_status": "delivered",
      "delivery_attempts": 1,
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 10
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/alerts?symbol=BTC&limit=20"
```

## Rule Types

### price_threshold

Triggers when price crosses a threshold.

```json
{
  "rule_type": "price_threshold",
  "config": {
    "threshold": 50000,
    "operator": ">="  // or "<="
  }
}
```

### percent_move

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

### candle_close

Triggers when candle close meets condition.

```json
{
  "rule_type": "candle_close",
  "config": {
    "value": 50000,
    "operator": ">="  // or "<="
  }
}
```

### macd_cross

Triggers on MACD signal line crossover.

```json
{
  "rule_type": "macd_cross",
  "config": {
    "fast_period": 12,
    "slow_period": 26,
    "signal_period": 9,
    "crossover_type": "bullish"  // or "bearish"
  }
}
```

