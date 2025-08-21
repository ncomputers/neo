from __future__ import annotations

"""Guest-facing order routes backed by tenant databases."""

from typing import AsyncGenerator, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.tenant import get_engine
from .events import event_bus
from .hooks import order_rejection
from .repos_sqlalchemy import orders_repo_sql
from .utils.responses import ok
from .routes_metrics import orders_created_total


router = APIRouter(prefix="/g")


class OrderLine(BaseModel):
    """Single line item for a guest order."""

    item_id: str
    qty: int


class OrderPayload(BaseModel):
    """Payload containing the items being ordered."""

    items: List[OrderLine]


async def get_tenant_id() -> str:
    """Resolve the tenant identifier for the current request.

    This is a placeholder implementation and will be replaced when tenant
    resolution is wired in.
    """

    return "demo"  # TODO: derive from request context


async def get_tenant_session(tenant_id: str = Depends(get_tenant_id)) -> AsyncGenerator[AsyncSession, None]:
    """Yield an ``AsyncSession`` bound to the tenant's database."""

    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with sessionmaker() as session:  # pragma: no cover - simple generator
        yield session


@router.post("/{table_token}/order")
async def create_guest_order(
    table_token: str,
    payload: OrderPayload,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    """Create a new order for ``table_token`` within the tenant context."""

    lines = [line.model_dump() for line in payload.items]
    try:
        order_id = await orders_repo_sql.create_order(session, table_token, lines)
    except ValueError as exc:
        ip = request.client.host if request.client else "unknown"
        await order_rejection.on_rejected(ip, request.app.state.redis)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:  # optional pubsub notification
        await event_bus.publish(
            "order.placed", {"tenant_id": tenant_id, "table_token": table_token, "order_id": order_id}
        )
    except Exception:  # pragma: no cover - pubsub unavailable
        pass
    orders_created_total.inc()
    return ok({"order_id": order_id})
