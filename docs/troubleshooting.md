# Troubleshooting

Common issues and fixes.

## Worker Crashes on Startup

**Symptom:** Worker exits immediately, logs show `MissingGreenlet` error.

**Cause:** Rule objects accessed after session closes.

**Fix:** Already fixed in code - rules converted to dicts after loading. If still occurs, check `worker/main.py` `load_active_rules()` converts to dicts.

## Worker Not Fetching Candles

**Symptom:** No `yielded_candle` logs, candle count not increasing.

**Check:**
```bash
docker-compose logs worker | grep "fetch_latest_candle"
```

**Possible Causes:**
1. Hyperliquid API down - check `fetch_latest_candle_failed` logs
2. Network issue - verify worker can reach `api.hyperliquid.xyz`
3. Invalid symbol - check `SYMBOLS` env var matches Hyperliquid format (BTC, ETH)

**Fix:**
- Verify API: `curl -X POST https://api.hyperliquid.xyz/info -H "Content-Type: application/json" -d '{"type":"candleSnapshot","req":{"coin":"BTC","interval":"15m","startTime":1704067200000,"endTime":1704070800000}}'`
- Check worker config: `docker-compose exec worker env | grep SYMBOLS`

## Rules Not Triggering

**Symptom:** Rules exist, candles processed, but no alerts created.

**Check:**
```bash
# Verify rule is active
curl "http://localhost:8000/api/v1/rules?symbol=BTC&is_active=true"

# Check if rule fired recently
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT * FROM alerts WHERE rule_id='<rule-id>' ORDER BY triggered_at DESC LIMIT 5;"
```

**Possible Causes:**
1. Cooldown active - check `cooldown_seconds` and last alert time
2. Idempotency window - same rule+window already fired
3. Rule condition not met - verify config matches current price

**Fix:**
- Reduce cooldown: `PUT /api/v1/rules/<id>` with `{"cooldown_seconds": 0}`
- Check rule config matches expected behavior
- Verify candles exist: `SELECT * FROM candles WHERE symbol='BTC' ORDER BY timestamp DESC LIMIT 5;`

## Webhook Delivery Failing

**Symptom:** Alerts created but `delivery_status='pending'` or `'failed'`.

**Check:**
```bash
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT a.id, a.delivery_status, a.delivery_attempts, ada.response_code, ada.error FROM alerts a LEFT JOIN alert_delivery_attempts ada ON a.id=ada.alert_id WHERE a.delivery_status != 'delivered' ORDER BY a.created_at DESC LIMIT 10;"
```

**Possible Causes:**
1. Invalid webhook URL - check `response_code` in attempts table
2. Discord rate limiting - check for 429 responses
3. Network timeout - check `latency_ms` in attempts table

**Fix:**
- Verify webhook URL: `curl -X POST <webhook_url> -d '{"test":true}'`
- Check Discord webhook is active (not deleted)
- Wait for retry (exponential backoff)

## Database Connection Errors

**Symptom:** `connection refused` or `relation does not exist` errors.

**Check:**
```bash
docker-compose ps postgres
docker-compose logs postgres | tail -20
```

**Fix:**
- Ensure postgres is healthy: `docker-compose ps postgres` shows "Healthy"
- Check migrations ran: `docker-compose logs api | grep "Migration completed"`
- Verify DATABASE_URL matches docker-compose service name (`postgres`, not `localhost`)

## API Returns 422 Validation Error

**Symptom:** POST/PUT requests return 422 with validation details.

**Common Issues:**
- Missing required field (e.g., `symbol` for `/candles`)
- Invalid enum value (e.g., `operator` must be `">="` or `"<="`)
- Invalid config structure for rule type

**Fix:**
- Check request body matches API spec in `docs/api.md`
- Verify rule config matches rule type requirements
- Check API logs: `docker-compose logs api | tail -20`

## Migration Errors

**Symptom:** `type already exists` or `relation already exists` errors.

**Cause:** Migration idempotency issue or manual schema changes.

**Fix:**
- Check current revision: `docker-compose exec api python -m alembic current`
- If stuck, manually fix schema or reset:
  ```bash
  docker-compose down -v  # WARNING: deletes data
  docker-compose up -d
  ```

## Worker Restarts Continuously

**Symptom:** `docker-compose ps worker` shows restart count increasing.

**Check:**
```bash
docker-compose logs worker | tail -50
```

**Common Causes:**
- Database not ready - check `wait_for_db.py` logs
- Missing migrations - check API logs for migration errors
- Code error - check for Python exceptions in logs

**Fix:**
- Ensure postgres is healthy before worker starts
- Check API completed migrations
- Review error logs for specific exception

## Candles API Returns Empty

**Symptom:** `GET /candles?symbol=BTC` returns `{"candles": [], "total": 0}`.

**Check:**
```bash
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT COUNT(*) FROM candles WHERE symbol='BTC';"
```

**Possible Causes:**
1. No candles ingested yet - worker just started
2. Wrong symbol - check case (API expects uppercase)
3. Wrong interval - default is 900s (15m)

**Fix:**
- Wait for worker to poll (60s interval)
- Use uppercase symbol: `symbol=BTC` not `symbol=btc`
- Check interval matches: `interval_seconds=900`

