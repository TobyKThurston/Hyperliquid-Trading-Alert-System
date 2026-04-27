"""Create a DB-backed API key.

Usage:
    python scripts/create_api_key.py "prod-dashboard" --rpm 120

Prints the raw key exactly once. Store it somewhere safe — the DB only
keeps the SHA-256 hash.
"""
import argparse
import asyncio
import hashlib
import secrets

from db.base import AsyncSessionLocal
from db.models import ApiKey


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new API key.")
    parser.add_argument("name", help="Human label (e.g. 'prod-dashboard')")
    parser.add_argument("--rpm", type=int, default=60, help="Requests per minute")
    args = parser.parse_args()

    raw_key = "pk_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    async with AsyncSessionLocal() as db:
        api_key = ApiKey(
            name=args.name,
            key_hash=key_hash,
            requests_per_minute=args.rpm,
            is_active=True,
        )
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)

    print(f"id:    {api_key.id}")
    print(f"name:  {api_key.name}")
    print(f"rpm:   {api_key.requests_per_minute}")
    print(f"key:   {raw_key}")
    print()
    print("Save the key now — it cannot be retrieved later.")


if __name__ == "__main__":
    asyncio.run(main())
