from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .deps.tenant import get_tenant_id
from .domain import OrderStatus
from .models_tenant import MenuItem, Order, OrderItem, Table
from .db.tenant import get_engine
from .utils.responses import ok
from .utils.audit import audit
from .routes_kds import _transition_order

router = APIRouter(prefix="/kds")


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


@router.get("/expo")
async def list_expo(tenant_id: str = Depends(get_tenant_id)) -> dict:
    async with _session(tenant_id) as session:
        result = await session.execute(
            select(
                Order.id,
                Table.code,
                Order.ready_at,
                MenuItem.allergens,
            )
            .join(Table, Order.table_id == Table.id)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .join(MenuItem, MenuItem.id == OrderItem.item_id)
            .where(Order.status == OrderStatus.READY.value)
            .order_by(Order.ready_at)
        )
        rows = result.all()

    now = datetime.now(timezone.utc)
    tickets: dict[int, dict] = {}
    for row in rows:
        info = tickets.setdefault(
            row.id,
            {
                "order_id": row.id,
                "table": row.code,
                "ready_at": row.ready_at,
                "allergen_badges": set(),
            },
        )
        if row.allergens:
            info["allergen_badges"].update(row.allergens)

    for ticket in tickets.values():
        ready_at = ticket.pop("ready_at")
        if ready_at and ready_at.tzinfo is None:
            ready_at = ready_at.replace(tzinfo=timezone.utc)
        ticket["age_s"] = (now - ready_at).total_seconds() if ready_at else 0.0
        ticket["allergen_badges"] = sorted(ticket["allergen_badges"])

    return ok({"tickets": list(tickets.values())})


@router.post("/expo/{order_id}/picked")
@audit("expo.picked")
async def mark_picked(order_id: int, tenant_id: str = Depends(get_tenant_id)) -> dict:
    return await _transition_order(tenant_id, order_id, OrderStatus.SERVED)
