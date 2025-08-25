"""Owner dashboard routes."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.replica import read_only, replica_session
from .db.tenant import get_engine
from .models_master import Tenant
from .repos_sqlalchemy import dashboard_repo_sql

router = APIRouter()


@asynccontextmanager
async def _session(tenant_id: str):
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


async def _get_timezone(tenant_id: str) -> str:
    async with replica_session() as session:
        tenant = await session.get(Tenant, tenant_id)
        if tenant is None:
            raise HTTPException(status_code=404, detail="tenant not found")
        return tenant.timezone or os.getenv("DEFAULT_TZ", "UTC")


@router.get("/api/outlet/{tenant_id}/dashboard/tiles")
@read_only
async def owner_dashboard_tiles(tenant_id: str, request: Request, force: bool = False):
    tz = await _get_timezone(tenant_id)
    redis = request.app.state.redis
    cache_key = f"dash:tiles:{tenant_id}"
    if not force:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    today = datetime.now(ZoneInfo(tz)).date()
    async with _session(tenant_id) as session:
        data = await dashboard_repo_sql.tiles_today(session, today, tz)
    await redis.set(cache_key, json.dumps(data), ex=30)
    return data
