from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .pdf.render import render_template
from .routes_counter import get_session_from_path
from .models_tenant import CounterOrder, CounterOrderItem, Counter

router = APIRouter(prefix="/api/outlet/{tenant_id}")


@router.get("/kot/{order_id}.pdf")
async def kot_pdf(
    tenant_id: str,
    order_id: int,
    size: Literal["80mm"] = "80mm",
    session: AsyncSession = Depends(get_session_from_path),
) -> Response:
    """Return a printable KOT for ``order_id``."""

    result = await session.execute(
        select(CounterOrder.id, CounterOrder.placed_at, Counter.code)
        .join(Counter, Counter.id == CounterOrder.counter_id)
        .where(CounterOrder.id == order_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail="order not found")
    order_id_db, placed_at, counter_code = row

    items_result = await session.execute(
        select(CounterOrderItem.name_snapshot, CounterOrderItem.qty).where(
            CounterOrderItem.order_id == order_id
        )
    )
    items = [{"name": name, "qty": qty} for name, qty in items_result.all()]

    kot = {
        "order_id": order_id_db,
        "counter_code": counter_code,
        "placed_at": placed_at.isoformat() if placed_at else "",
        "items": items,
        "notes": "",
    }

    content, mimetype = render_template("kot_80mm.html", {"kot": kot})
    return Response(content, media_type=mimetype)
