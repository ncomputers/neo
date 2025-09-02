#!/usr/bin/env python3
"""Connectivity smoke check for Postgres and Redis."""
from __future__ import annotations

import os
import sys

import psycopg2
import redis


def check_postgres() -> None:
    dsn = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_MASTER_URL")
    if not dsn:
        print("DATABASE_URL or POSTGRES_MASTER_URL not set", file=sys.stderr)
        raise SystemExit(1)
    try:
        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
    except Exception as exc:
        print(f"Postgres connection failed: {exc}", file=sys.stderr)
        raise SystemExit(1)


def check_redis() -> None:
    url = os.getenv("REDIS_URL")
    if url:
        client = redis.from_url(url)
    else:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        client = redis.Redis(host=host, port=port, db=db)
    try:
        client.ping()
    except Exception as exc:
        print(f"Redis connection failed: {exc}", file=sys.stderr)
        raise SystemExit(1)


def main() -> None:
    check_postgres()
    check_redis()
    print("ok")


if __name__ == "__main__":
    main()
