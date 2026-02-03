# Runbook

Operations guide for Pulse alerting backend.

## Logs

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f worker
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 worker

# Search for errors
docker-compose logs worker | grep -i error
```

### Log Format

Logs are JSON-structured. Key events:

- `worker_starting`: Worker started
- `loaded_rules`: Rules loaded (check count)
- `yielded_candle`: New candle processed
- `alert_triggered`: Rule fired
- `discord_webhook_sent`: Alert delivered
- `alert_delivered`: Retry succeeded
- `alert_failed_max_retries`: Alert failed after max attempts

## Troubleshooting

### Worker Not Processing Candles

1. Check worker is running: `docker-compose ps worker`
2. Check logs for errors: `docker-compose logs worker | grep -i error`
3. Verify Hyperliquid API is reachable:
   ```bash
   curl -X POST https://api.hyperliquid.xyz/info \
     -H "Content-Type: application/json" \
     -d '{"type":"candleSnapshot","req":{"coin":"BTC","interval":"15m","startTime":1704067200000,"endTime":1704070800000}}'
   ```
4. Check database connection: `docker-compose logs worker | grep "Database is ready"`

### Alerts Not Firing

1. Verify rule is active:
   ```bash
   curl "http://localhost:8000/api/v1/rules?symbol=BTC&is_active=true"
   ```
2. Check cooldown: Rule won't fire if within cooldown period
3. Check idempotency: Same rule+window won't fire twice (by design)
4. Verify candles exist:
   ```bash
   docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT COUNT(*) FROM candles WHERE symbol='BTC';"
   ```

### Webhook Delivery Failing

1. Check delivery attempts:
   ```bash
   docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT * FROM alert_delivery_attempts ORDER BY created_at DESC LIMIT 10;"
   ```
2. Check response codes and errors in `alert_delivery_attempts` table
3. Verify webhook URL is valid:
   ```bash
   curl -X POST <webhook_url> -d '{"test":true}'
   ```
4. Check retry logs: `docker-compose logs worker | grep "retry"`

## Retries

### How Retries Work

1. Failed alerts are marked `delivery_status='pending'`
2. Background task polls every 30s (configurable via `RETRY_POLL_INTERVAL`)
3. Exponential backoff: `2^(attempts-1)` seconds, max 32s
4. Max attempts: 5 (configurable via `RETRY_BACKOFF_MAX`)
5. After max attempts, alert marked `delivery_status='failed'`

### Retry Status

```bash
# Check pending alerts
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT COUNT(*) FROM alerts WHERE delivery_status='pending';"

# Check failed alerts
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT COUNT(*) FROM alerts WHERE delivery_status='failed';"

# View retry attempts
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT alert_id, attempt_no, status, response_code, error FROM alert_delivery_attempts ORDER BY created_at DESC LIMIT 10;"
```

## Validating Ingestion

### Check Candle Ingestion

```bash
# Count candles per symbol
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT symbol, COUNT(*) FROM candles GROUP BY symbol;"

# Check latest candle timestamp
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT symbol, MAX(timestamp) FROM candles GROUP BY symbol;"

# Verify worker cursors
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT * FROM worker_cursors;"
```

### Expected Behavior

- Worker polls every 60 seconds
- New candles appear within 1-2 minutes of being available
- Cursor timestamps update after each candle processed

## Alert Delivery Verification

### Check Alert Creation

```bash
# Recent alerts
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT id, symbol, triggered_at, delivery_status FROM alerts ORDER BY triggered_at DESC LIMIT 10;"
```

### Check Delivery Attempts

```bash
# All attempts for an alert
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT * FROM alert_delivery_attempts WHERE alert_id='<alert-id>';"
```

### Verify Webhook Received

- Check Discord channel for webhook messages
- Check generic webhook endpoint logs
- Verify `response_code=200` in `alert_delivery_attempts`

## Rotating Webhooks

### Discord Webhook Rotation

1. Create new webhook in Discord (Server Settings > Integrations > Webhooks)
2. Update rule via API:
   ```bash
   curl -X PUT "http://localhost:8000/api/v1/rules/<rule-id>" \
     -H "X-API-Key: your-key" \
     -H "Content-Type: application/json" \
     -d '{"discord_webhook_url": "https://discord.com/api/webhooks/NEW_ID/NEW_TOKEN"}'
   ```
3. Revoke old webhook in Discord

### Generic Webhook Rotation

Same process, update `generic_webhook_url` field.

## Health Checks

### API Health

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

### Database Health

```bash
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT 1;"
```

### Worker Health

Check logs for `retry_scheduler_started` and recent `yielded_candle` events.

## Common Operations

### Restart Worker

```bash
docker-compose restart worker
```

### Reload Rules (No Restart)

Rules are loaded on startup. To reload, restart worker or update rules via API.

### Clear Old Data

```bash
# Delete old candles (older than 7 days)
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "DELETE FROM candles WHERE timestamp < NOW() - INTERVAL '7 days';"

# Delete old alerts (older than 30 days)
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "DELETE FROM alerts WHERE created_at < NOW() - INTERVAL '30 days';"
```

