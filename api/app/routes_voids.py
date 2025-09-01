"""Endpoints for controlled cancellation (void/return) approvals."""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .auth import User
from .db.tenant import get_engine
from .domain import OrderStatus
from .models_tenant import Invoice, Order, OrderItem
from .routes_auth_2fa import stepup_guard
from .utils.audit import audit
from .utils.responses import ok

router = APIRouter()

# Require manager role and honor 2FA step-up if enabled
manager_guard = stepup_guard("manager")


class VoidRequest(BaseModel):
    """Payload when staff requests a void."""

    reason: str


_pending: dict[int, str] = {}


async def get_session_from_path(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Yield an ``AsyncSession`` for ``tenant_id``."""

    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


@router.post("/api/outlet/{tenant_id}/orders/{order_id}/void/request")
@audit("order.void.request")
async def request_void(
    tenant_id: str,
    order_id: int,
    payload: VoidRequest,
    session: AsyncSession = Depends(get_session_from_path),
) -> dict:
    """Record a void request for ``order_id`` with ``reason``."""

    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    _pending[order_id] = payload.reason
    return ok({"status": "pending"})


@router.post("/api/outlet/{tenant_id}/orders/{order_id}/void/approve")
@audit("order.void.approve")
async def approve_void(
    tenant_id: str,
    order_id: int,
    user: User = Depends(manager_guard),
    session: AsyncSession = Depends(get_session_from_path),
    confirm: bool = Query(False),
) -> dict:
    """Approve a pending void and adjust invoice totals."""

    if not confirm:
        raise HTTPException(status_code=400, detail="confirmation required")

    reason = _pending.pop(order_id, None)
    if reason is None:
        raise HTTPException(status_code=404, detail="void not requested")

    total = await session.scalar(
        select(
            func.coalesce(func.sum(OrderItem.price_snapshot * OrderItem.qty), 0)
        ).where(OrderItem.order_id == order_id)
    )

    await session.execute(
        update(Order)
        .where(Order.id == order_id)
        .values(status=OrderStatus.CANCELLED.value)
    )

    result = await session.execute(
        select(Invoice).where(Invoice.order_group_id == order_id)
    )
    invoice = result.scalar_one_or_none()
    if invoice:
        invoice.total = invoice.total - total
        bill = invoice.bill_json or {}
        bill["subtotal"] = float(bill.get("subtotal", 0) - float(total))
        bill["total"] = float(bill.get("total", 0) - float(total))
        invoice.bill_json = bill
    await session.commit()
    return ok({"status": "voided", "reason": reason})
