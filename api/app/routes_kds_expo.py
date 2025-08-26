from __future__ import annotations

from datetime import datetime, timezone

from domain import OrderStatus
from fastapi import APIRouter, HTTPException
from models_tenant import MenuItem, Order, OrderItem, Table
from sqlalchemy import select, update
from utils.audit import audit
from utils.responses import ok

from .routes_kds import _session

router = APIRouter()


@router.get("/api/outlet/{tenant_id}/kds/expo")
@audit("list_kds_expo")
async def list_expo(tenant_id: str) -> dict:
    """Return ready orders with aging and allergen badges."""

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

    tickets: dict[int, dict] = {}
    now = datetime.now(timezone.utc)

    for row in rows:
        info = tickets.setdefault(
            row.id,
            {
                "order_id": row.id,
                "table": row.code,
                "ready_at": row.ready_at,
                "allergens": set(),
            },
        )
        if row.allergens:
            info["allergens"].update(row.allergens)

    orders_out = []
    for info in tickets.values():
        ready_at = info.pop("ready_at")
        if ready_at and ready_at.tzinfo is None:
            ready_at = ready_at.replace(tzinfo=timezone.utc)
        age_s = (now - ready_at).total_seconds() if ready_at else 0.0
        orders_out.append(
            {
                "order_id": info["order_id"],
                "table": info["table"],
                "age_s": age_s,
                "allergen_badges": sorted(info["allergens"]),
            }
        )

    return ok({"orders": orders_out})


@router.post("/api/outlet/{tenant_id}/kds/expo/{order_id}/picked")
@audit("expo.picked")
async def pick_order(tenant_id: str, order_id: int) -> dict:
    """Mark a ready order as picked up."""
    async with _session(tenant_id) as session:
        result = await session.execute(select(Order.status).where(Order.id == order_id))
        current = result.scalar_one_or_none()
        if current is None:
            raise HTTPException(status_code=404, detail="order not found")
        if current != OrderStatus.READY:
            raise HTTPException(status_code=400, detail="invalid transition")
        await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status=OrderStatus.SERVED.value)
        )
        await session.commit()
    return ok({"status": OrderStatus.SERVED.value})

