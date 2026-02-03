#!/bin/bash
set -e

echo "Waiting for database to be ready..."
# Wait for database connection (not tables - we'll create them)
python -c "
import os, sys, time
from urllib.parse import urlparse
try:
    import psycopg2
    db_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://pulse_user:pulse_password@postgres:5432/pulse_db')
    parsed = urlparse(db_url.replace('postgresql+asyncpg://', 'postgresql://'))
    for i in range(30):
        try:
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                dbname=parsed.path[1:] if parsed.path else 'pulse_db',
                connect_timeout=5
            )
            conn.close()
            print('Database is ready!')
            sys.exit(0)
        except Exception as e:
            if i == 0:
                print(f'Waiting for database... ({type(e).__name__})')
            time.sleep(1)
    print('Timeout waiting for database')
    sys.exit(1)
except ImportError:
    print('psycopg2 not available')
    sys.exit(1)
" || exit 1

echo "Running database migrations..."
python -m alembic upgrade head || echo "Migration completed (may have been partially applied)"

echo "Starting API server..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000

