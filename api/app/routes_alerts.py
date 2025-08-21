from __future__ import annotations

"""Routes for managing alert rules and viewing notification outbox."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .auth import User, role_required
from .db.tenant import get_engine
from .models_tenant import AlertRule, NotificationOutbox
from .utils.responses import ok
from .utils.audit import audit

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
@audit("create_alert_rule")
async def create_rule(
    tenant_id: str,
    payload: RuleCreate,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    rule = AlertRule(**payload.model_dump())
    async with _session(tenant_id) as session:
        session.add(rule)
        await session.commit()
    return ok({"id": rule.id})


@router.get("/api/outlet/{tenant_id}/alerts/rules")
@audit("list_alert_rules")
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


@router.get("/api/outlet/{tenant_id}/alerts/outbox")
@audit("list_alert_outbox")
async def list_outbox(
    tenant_id: str,
    status: str = Query("queued"),
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    async with _session(tenant_id) as session:
        result = await session.execute(
            select(NotificationOutbox)
            .where(NotificationOutbox.status == status)
            .order_by(NotificationOutbox.created_at.desc())
            .limit(50)
        )
        rows = [
            {
                "id": o.id,
                "event": o.event,
                "payload": o.payload,
                "channel": o.channel,
                "target": o.target,
                "status": o.status,
                "created_at": o.created_at,
                "delivered_at": o.delivered_at,
            }
            for o in result.scalars().all()
        ]
    return ok(rows)
