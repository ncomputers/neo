from __future__ import annotations

"""Routes for ingesting queued orders in batch."""

from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import UUID4, BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.tenant import get_engine
from .repos_sqlalchemy import orders_repo_sql
from .utils.responses import ok

router = APIRouter()


class OrderLine(BaseModel):
    """Single line item for an order."""

    item_id: str
    qty: int


class QueuedOrder(BaseModel):
    """Order payload queued for later ingestion."""

    op_id: UUID4
    table_code: str
    items: List[OrderLine]


class BatchPayload(BaseModel):
    """Batch of queued orders."""

    orders: List[QueuedOrder]


@router.post("/api/outlet/{tenant_id}/orders/batch")
async def ingest_orders_batch(
    request: Request, tenant_id: str, payload: BatchPayload
) -> dict:
    """Persist multiple queued orders for ``tenant_id``.

    The batch is limited to 20 orders to bound request sizes.
    """

    if len(payload.orders) > 20:
        raise HTTPException(status_code=400, detail="Too many orders")

    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    redis = request.app.state.redis
    async with sessionmaker() as session:
        order_ids = []
        for order in payload.orders:
            key = f"op:{order.op_id}"
            cached = await redis.get(key)
            if cached:
                order_ids.append(int(cached))
                continue
            lines = [line.model_dump() for line in order.items]
            order_id = await orders_repo_sql.create_order(
                session, order.table_code, lines
            )
            order_ids.append(order_id)
            await redis.set(key, str(order_id), ex=3600)
    return ok({"order_ids": order_ids})
