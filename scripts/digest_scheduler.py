#!/usr/bin/env python3
"""Trigger the daily KPI digest for each active tenant at 09:00 local time."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, time, timedelta
from pathlib import Path
import sys
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))

from app.models_master import Tenant  # type: ignore  # noqa: E402
from scripts import daily_digest  # type: ignore  # noqa: E402

try:  # Optional Redis client
    import redis.asyncio as redis  # type: ignore
except Exception:  # pragma: no cover - redis not installed
    redis = None  # type: ignore

REDIS_KEY_PREFIX = "digest:last:"


def _now(tz: ZoneInfo) -> datetime:
    """Return current time in ``tz`` (for monkeypatching in tests)."""
    return datetime.now(tz)


async def run_once(engine, redis_client) -> None:
    """Run a single scheduling cycle."""
    async with AsyncSession(engine) as session:
        rows = await session.execute(
            select(Tenant.name, Tenant.timezone).where(Tenant.status == "active")
        )
        tenants = rows.all()

    for name, tz in tenants:
        tzinfo = ZoneInfo(tz or "UTC")
        now_local = _now(tzinfo)
        if now_local.time() < time(9, 0):
            continue
        yesterday = (now_local.date() - timedelta(days=1)).isoformat()
        key = f"{REDIS_KEY_PREFIX}{name}"
        last = await redis_client.get(key)
        if last is not None and last.decode() == yesterday:
            continue
        providers = tuple(daily_digest.PROVIDERS.keys())
        await daily_digest.main(name, yesterday, providers=providers)
        await redis_client.set(key, yesterday)


async def run() -> None:
    """Entry point used by the systemd service."""
    master_url = os.environ["POSTGRES_URL"]
    redis_url = os.environ.get("REDIS_URL")
    if redis is None or redis_url is None:
        raise RuntimeError("redis client not available")
    engine = create_async_engine(master_url)
    redis_client = redis.from_url(redis_url)
    try:
        await run_once(engine, redis_client)
    finally:
        await engine.dispose()
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(run())
