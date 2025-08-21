from __future__ import annotations

"""Admin routes for managing alert rules."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .auth import User, role_required
from .db.tenant import get_engine
from .models_tenant import AlertRule
from .utils.responses import ok

router = APIRouter()


class RuleCreate(BaseModel):
    event: str
    channel: str
    target: str
    enabled: bool = True


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


@router.post("/api/outlet/{tenant_id}/alerts/rules")
async def create_rule(
    tenant_id: str,
    payload: RuleCreate,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    rule = AlertRule(**payload.dict())
    async with _session(tenant_id) as session:
        session.add(rule)
        await session.commit()
    return ok({"id": rule.id})


@router.get("/api/outlet/{tenant_id}/alerts/rules")
async def list_rules(
    tenant_id: str,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    async with _session(tenant_id) as session:
        result = await session.execute(select(AlertRule))
        rules = [
            {
                "id": r.id,
                "event": r.event,
                "channel": r.channel,
                "target": r.target,
                "enabled": r.enabled,
            }
            for r in result.scalars().all()
        ]
    return ok(rules)
