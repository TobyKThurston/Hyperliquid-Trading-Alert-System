# Local Development

## Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for running tests locally)

## Quick Start

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Start services
docker-compose up -d

# 3. Wait for migrations (API entrypoint runs them automatically)
docker-compose logs api | grep "Migration completed"

# 4. Verify health
curl http://localhost:8000/health
```

## Development Workflow

### Running Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f worker

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose build api worker
docker-compose up -d
```

### Database Migrations

Migrations run automatically on API startup. To run manually:

```bash
# Check current revision
docker-compose exec api python -m alembic current

# Upgrade to latest
docker-compose exec api python -m alembic upgrade head

# Create new migration
docker-compose exec api python -m alembic revision --autogenerate -m "description"

# Downgrade one revision
docker-compose exec api python -m alembic downgrade -1
```

### Running Locally (Without Docker)

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Start PostgreSQL (or use Docker)
docker-compose up -d postgres

# 3. Set environment
export DATABASE_URL="postgresql+asyncpg://pulse_user:pulse_password@localhost:5432/pulse_db"
export API_KEY="test-key"
export LOG_LEVEL="DEBUG"

# 4. Run migrations
python -m alembic upgrade head

# 5. Run API (terminal 1)
python -m api.main

# 6. Run worker (terminal 2)
python -m worker.main
```

## Common Commands

```bash
# Check service status
docker-compose ps

# View API logs
docker-compose logs --tail=50 api

# View worker logs
docker-compose logs --tail=50 worker

# Restart worker
docker-compose restart worker

# Access database
docker-compose exec postgres psql -U pulse_user -d pulse_db

# Run tests
pytest

# Run tests with coverage
pytest --cov=. --cov-report=term-missing

# Format code
ruff format .

# Lint code
ruff check .
```

## Testing

Tests use in-memory SQLite. No database setup needed:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/integration/test_api_candles.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_candles"
```

## Debugging

```bash
# Check worker is processing candles
docker-compose logs worker | grep "yielded_candle"

# Check rules are loaded
docker-compose logs worker | grep "loaded_rules"

# Check for errors
docker-compose logs worker | grep -i error

# Query database directly
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT * FROM rules;"
docker-compose exec postgres psql -U pulse_user -d pulse_db -c "SELECT COUNT(*) FROM candles;"
```

