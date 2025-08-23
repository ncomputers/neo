"""Owner dashboard charts routes."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import json
import os

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from zoneinfo import ZoneInfo

from .db.tenant import get_engine
from .db.master import get_session as get_master_session
from .models_master import Tenant
from .repos_sqlalchemy import dashboard_repo_sql

router = APIRouter()


@asynccontextmanager
async def _session(tenant_id: str):
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


async def _get_timezone(tenant_id: str) -> str:
    async with get_master_session() as session:
        tenant = await session.get(Tenant, tenant_id)
        if tenant is None:
            raise HTTPException(status_code=404, detail="tenant not found")
        return tenant.timezone or os.getenv("DEFAULT_TZ", "UTC")


@router.get("/api/outlet/{tenant_id}/dashboard/charts")
async def owner_dashboard_charts(
    tenant_id: str, request: Request, range: int = 7, force: bool = False
):
    if range not in (7, 30, 90):
        raise HTTPException(status_code=400, detail="invalid range")
    tz = await _get_timezone(tenant_id)
    redis = request.app.state.redis
    cache_key = f"dash:charts:{tenant_id}:{range}"
    if not force:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    today = datetime.now(ZoneInfo(tz)).date()
    start = today - timedelta(days=range - 1)
    async with _session(tenant_id) as session:
        data = await dashboard_repo_sql.charts_range(session, start, today, tz)
    await redis.set(cache_key, json.dumps(data), ex=300)
    return data
