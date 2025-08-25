"""Owner dashboard charts routes."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import json
import os
import statistics
import builtins

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
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
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
        data = await dashboard_repo_sql.charts_range(
            session, start, today, tz, use_rollup=True
        )
    sales_series = data.get("series", {}).get("sales", [])
    sales = [pt["v"] for pt in sales_series]
    dates = [pt["d"] for pt in sales_series]
    ma7 = []
    ma30 = []
    for i, d in enumerate(dates):
        w7 = sales[max(0, i - 6) : i + 1]
        w30 = sales[max(0, i - 29) : i + 1]
        ma7.append({"d": d, "v": statistics.mean(w7) if w7 else 0.0})
        ma30.append({"d": d, "v": statistics.mean(w30) if w30 else 0.0})
    data.setdefault("series", {})["sales_ma7"] = ma7
    data.setdefault("series", {})["sales_ma30"] = ma30
    anomalies = []
    for i in builtins.range(6, len(sales)):
        window = sales[i - 6 : i + 1]
        avg = statistics.mean(window)
        std = statistics.pstdev(window)
        if std and abs(sales[i] - avg) > 2 * std:
            anomalies.append(dates[i])
    data["anomalies"] = anomalies
    await redis.set(cache_key, json.dumps(data), ex=300)
    return data
