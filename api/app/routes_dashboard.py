"""Owner dashboard routes."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
import os

from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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


@router.get("/api/outlet/{tenant_id}/dashboard/tiles")
async def owner_dashboard_tiles(tenant_id: str):
    tz = await _get_timezone(tenant_id)
    today = date.today()
    async with _session(tenant_id) as session:
        data = await dashboard_repo_sql.tiles_today(session, today, tz)
    return data
