from __future__ import annotations

"""Admin routes for inspecting and operating the notifications outbox."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .auth import User, role_required
from .db.tenant import get_engine
from .models_tenant import NotificationDLQ, NotificationOutbox
from .utils.pagination import Pagination
from .utils.pagination import pagination as paginate
from .utils.responses import ok
from .utils.scrub import scrub_payload

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


@router.get("/api/outlet/{tenant_id}/outbox")
async def list_outbox(
    tenant_id: str,
    status: str = Query("pending"),
    page: Pagination = Depends(paginate),
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    status_map = {"pending": "queued"}
    db_status = status_map.get(status, status)
    async with _session(tenant_id) as session:
        stmt = (
            select(NotificationOutbox)
            .where(NotificationOutbox.status == db_status)
            .order_by(NotificationOutbox.id.desc())
            .limit(page.limit)
        )
        if page.cursor:
            stmt = stmt.where(NotificationOutbox.id < page.cursor)
        result = await session.execute(stmt)
        rows = [
            {
                "id": o.id,
                "event": o.event,
                "payload": scrub_payload(o.payload),
                "channel": o.channel,
                "target": o.target,
                "status": o.status,
                "attempts": o.attempts,
                "next_attempt_at": o.next_attempt_at,
                "created_at": o.created_at,
                "delivered_at": o.delivered_at,
            }
            for o in result.scalars().all()
        ]
    return ok(rows)


@router.post("/api/outlet/{tenant_id}/outbox/{item_id}/retry")
async def retry_outbox(
    tenant_id: str,
    item_id: int,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    async with _session(tenant_id) as session:
        obj = await session.get(NotificationOutbox, item_id)
        if obj:
            obj.status = "queued"
            obj.attempts = 0
            obj.next_attempt_at = None
            obj.delivered_at = None
            session.add(obj)
            await session.commit()
    return ok({})


@router.get("/api/outlet/{tenant_id}/dlq")
async def list_dlq(
    tenant_id: str,
    page: Pagination = Depends(paginate),
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    async with _session(tenant_id) as session:
        stmt = (
            select(NotificationDLQ)
            .order_by(NotificationDLQ.id.desc())
            .limit(page.limit)
        )
        if page.cursor:
            stmt = stmt.where(NotificationDLQ.id < page.cursor)
        result = await session.execute(stmt)
        rows = [
            {
                "id": d.id,
                "original_id": d.original_id,
                "event": d.event,
                "channel": d.channel,
                "target": d.target,
                "payload": scrub_payload(d.payload),
                "error": d.error,
                "failed_at": d.failed_at,
            }
            for d in result.scalars().all()
        ]
    return ok(rows)


@router.post("/api/outlet/{tenant_id}/dlq/{item_id}/requeue")
async def requeue_dlq(
    tenant_id: str,
    item_id: int,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    async with _session(tenant_id) as session:
        dlq = await session.get(NotificationDLQ, item_id)
        if dlq:
            session.add(
                NotificationOutbox(
                    event=dlq.event,
                    payload=dlq.payload,
                    channel=dlq.channel,
                    target=dlq.target,
                    status="queued",
                    attempts=0,
                )
            )
            await session.delete(dlq)
            await session.commit()
    return ok({})


@router.delete("/api/outlet/{tenant_id}/dlq/{item_id}")
async def delete_dlq(
    tenant_id: str,
    item_id: int,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    async with _session(tenant_id) as session:
        dlq = await session.get(NotificationDLQ, item_id)
        if dlq:
            await session.delete(dlq)
            await session.commit()
    return ok({})
