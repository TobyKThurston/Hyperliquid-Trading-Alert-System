#!/usr/bin/env python3
"""Wait for database and tables to be ready."""

import os
import sys
import time
from urllib.parse import urlparse


def check_with_psycopg2():
    """Check database with psycopg2."""
    try:
        import psycopg2
    except ImportError:
        return False

    db_url = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://pulse_user:pulse_password@postgres:5432/pulse_db"
    )
    parsed = urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))

    for i in range(60):
        try:
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                dbname=parsed.path[1:] if parsed.path else "pulse_db",
                connect_timeout=5,
            )
            # Check if rules table exists
            cur = conn.cursor()
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'rules'
                )
                """
            )
            table_exists = cur.fetchone()[0]
            cur.close()
            conn.close()
            if table_exists:
                print("Database is ready and tables exist!")
                return True
            elif i == 0:
                print("Database connected but tables not ready yet...")
        except Exception as e:
            if i == 0:
                print(f"Waiting for database... ({type(e).__name__}: {e})")
        time.sleep(1)
    return False


def check_with_asyncpg():
    """Check database with asyncpg."""
    try:
        import asyncio

        import asyncpg
    except ImportError:
        return False

    async def check():
        db_url = os.getenv(
            "DATABASE_URL", "postgresql+asyncpg://pulse_user:pulse_password@postgres:5432/pulse_db"
        )
        parsed = urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))

        for i in range(60):
            try:
                conn = await asyncio.wait_for(
                    asyncpg.connect(
                        host=parsed.hostname,
                        port=parsed.port or 5432,
                        user=parsed.username,
                        password=parsed.password,
                        database=parsed.path[1:] if parsed.path else "pulse_db",
                    ),
                    timeout=5.0,
                )
                # Check if rules table exists
                table_exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'rules'
                    )
                    """
                )
                await conn.close()
                if table_exists:
                    print("Database is ready and tables exist!")
                    return True
                elif i == 0:
                    print("Database connected but tables not ready yet...")
            except Exception as e:
                if i == 0:
                    print(f"Waiting for database... ({type(e).__name__}: {e})")
            await asyncio.sleep(1)
        return False

    return asyncio.run(check())


# Try psycopg2 first, then asyncpg
if not check_with_psycopg2():
    if not check_with_asyncpg():
        print("Timeout waiting for database/tables")
        sys.exit(1)

sys.exit(0)
