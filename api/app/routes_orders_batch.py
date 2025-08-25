from __future__ import annotations

"""Routes for ingesting queued orders in batch."""

from typing import List, Set

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.tenant import get_engine
from .repos_sqlalchemy import orders_repo_sql
from .utils.responses import ok

router = APIRouter()


# Track processed operation identifiers to dedupe repeats
_processed_ops: Set[str] = set()


class OrderLine(BaseModel):
    """Single line item for an order."""

    item_id: str
    qty: int


class QueuedOrder(BaseModel):
    """Order payload queued for later ingestion."""

    op_id: str
    table_code: str
    items: List[OrderLine]


class BatchPayload(BaseModel):
    """Batch of queued orders."""

    orders: List[QueuedOrder]


@router.post("/api/outlet/{tenant_id}/orders/batch")
async def ingest_orders_batch(tenant_id: str, payload: BatchPayload) -> dict:
    """Persist multiple queued orders for ``tenant_id``.

    The batch is limited to 20 orders to bound request sizes.
    """

    if len(payload.orders) > 20:
        raise HTTPException(status_code=400, detail="Too many orders")

    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with sessionmaker() as session:
        order_ids = []
        for order in payload.orders:
            # Skip orders we've already processed
            if order.op_id in _processed_ops:
                continue
            _processed_ops.add(order.op_id)
            lines = [line.model_dump() for line in order.items]
            try:
                order_id = await orders_repo_sql.create_order(
                    session, order.table_code, lines
                )
            except ValueError as exc:
                status = 403 if str(exc) == "GONE_RESOURCE" else 400
                raise HTTPException(status_code=status, detail=str(exc)) from exc
            order_ids.append(order_id)
    return ok({"order_ids": order_ids})
