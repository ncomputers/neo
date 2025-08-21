"""Kitchen Display System related API routes.

These endpoints operate on tenant-specific databases and are currently
unwired into the main application. They provide order status transitions
used by the KDS workflow.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.tenant import get_engine
from domain import OrderStatus, can_transition
from models_tenant import Order, OrderItem
from repos_sqlalchemy import orders_repo_sql
from utils.responses import ok

router = APIRouter()


@asynccontextmanager
async def _session(tenant_id: str):
    """Yield an ``AsyncSession`` for the given ``tenant_id``."""
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


@router.get("/api/outlet/{tenant_id}/kds/queue")
async def list_queue(tenant_id: str) -> dict:
    """Return active orders for the KDS queue view."""
    async with _session(tenant_id) as session:
        orders = await orders_repo_sql.list_active(session)
    return ok(orders)


async def _transition_order(tenant_id: str, order_id: int, dest: OrderStatus) -> dict:
    """Transition an order to ``dest`` if allowed."""
    async with _session(tenant_id) as session:
        result = await session.execute(select(Order.status).where(Order.id == order_id))
        current = result.scalar_one_or_none()
        if current is None:
            raise HTTPException(status_code=404, detail="order not found")
        if not can_transition(OrderStatus(current), dest):
            raise HTTPException(status_code=400, detail="invalid transition")
        await orders_repo_sql.update_status(session, order_id, dest.value)
    return ok({"status": dest.value})


async def _transition_item(
    tenant_id: str, order_item_id: int, dest: OrderStatus
) -> dict:
    """Transition an order item to ``dest`` if allowed."""
    async with _session(tenant_id) as session:
        result = await session.execute(
            select(OrderItem.status).where(OrderItem.id == order_item_id)
        )
        current = result.scalar_one_or_none()
        if current is None:
            raise HTTPException(status_code=404, detail="order item not found")
        if not can_transition(OrderStatus(current), dest):
            raise HTTPException(status_code=400, detail="invalid transition")
        await session.execute(
            update(OrderItem)
            .where(OrderItem.id == order_item_id)
            .values(status=dest.value)
        )
        await session.commit()
    return ok({"status": dest.value})


@router.post("/api/outlet/{tenant_id}/kds/order/{order_id}/accept")
async def accept_order(tenant_id: str, order_id: int) -> dict:
    """Mark an order as accepted."""
    return await _transition_order(tenant_id, order_id, OrderStatus.ACCEPTED)


@router.post("/api/outlet/{tenant_id}/kds/order/{order_id}/progress")
async def progress_order(tenant_id: str, order_id: int) -> dict:
    """Move an order to ``IN_PROGRESS``."""
    return await _transition_order(tenant_id, order_id, OrderStatus.IN_PROGRESS)


@router.post("/api/outlet/{tenant_id}/kds/order/{order_id}/ready")
async def ready_order(tenant_id: str, order_id: int) -> dict:
    """Mark an order as ready."""
    return await _transition_order(tenant_id, order_id, OrderStatus.READY)


@router.post("/api/outlet/{tenant_id}/kds/order/{order_id}/serve")
async def serve_order(tenant_id: str, order_id: int) -> dict:
    """Mark an order as served."""
    return await _transition_order(tenant_id, order_id, OrderStatus.SERVED)


@router.post("/api/outlet/{tenant_id}/kds/item/{order_item_id}/accept")
async def accept_item(tenant_id: str, order_item_id: int) -> dict:
    """Mark an order item as accepted."""
    return await _transition_item(tenant_id, order_item_id, OrderStatus.ACCEPTED)


@router.post("/api/outlet/{tenant_id}/kds/item/{order_item_id}/progress")
async def progress_item(tenant_id: str, order_item_id: int) -> dict:
    """Move an order item to ``IN_PROGRESS``."""
    return await _transition_item(tenant_id, order_item_id, OrderStatus.IN_PROGRESS)


@router.post("/api/outlet/{tenant_id}/kds/item/{order_item_id}/ready")
async def ready_item(tenant_id: str, order_item_id: int) -> dict:
    """Mark an order item as ready."""
    return await _transition_item(tenant_id, order_item_id, OrderStatus.READY)


@router.post("/api/outlet/{tenant_id}/kds/item/{order_item_id}/serve")
async def serve_item(tenant_id: str, order_item_id: int) -> dict:
    """Mark an order item as served."""
    return await _transition_item(tenant_id, order_item_id, OrderStatus.SERVED)
