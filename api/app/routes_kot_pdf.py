from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.tenant import get_engine
from .pdf.render import render_kot
from .models_tenant import Order, OrderItem, Table

router = APIRouter()


@asynccontextmanager
async def _session(tenant: str):
    engine = get_engine(tenant)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


@router.get("/api/outlet/{tenant}/kot/{order_id}.pdf")
async def kot_pdf(
    tenant: str, order_id: int, size: Literal["80mm"] = "80mm"
) -> Response:
    async with _session(tenant) as session:
        result = await session.execute(
            select(Order.table_id, Order.placed_at).where(Order.id == order_id)
        )
        row = result.first()
        if row is None:
            raise HTTPException(status_code=404, detail="order not found")
        table_id, placed_at = row

        table_code = await session.scalar(
            select(Table.code).where(Table.id == table_id)
        )
        items_result = await session.execute(
            select(OrderItem.name_snapshot, OrderItem.qty).where(
                OrderItem.order_id == order_id
            )
        )
        items = [{"name": r.name_snapshot, "qty": r.qty} for r in items_result]

    kot = {
        "order_id": order_id,
        "table_code": table_code or "",
        "placed_at": placed_at.isoformat() if placed_at else "",
        "items": items,
        "notes": "",
    }
    content, mimetype = render_kot(kot, size=size)
    return Response(content, media_type=mimetype)
