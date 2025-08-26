from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models_tenant import (
    Counter,
    CounterOrder,
    CounterOrderItem,
    Order,
    OrderItem,
    Room,
    RoomOrder,
    RoomOrderItem,
    Table,
)
from .pdf.render import render_template
from .routes_counter import get_session_from_path

router = APIRouter(prefix="/api/outlet/{tenant_id}")


@router.get("/kot/{order_id}.pdf")
async def kot_pdf(
    tenant_id: str,
    order_id: int,
    request: Request,
    size: Literal["80mm"] = "80mm",
    session: AsyncSession = Depends(get_session_from_path),
) -> Response:
    """Return a printable KOT for ``order_id``.

    Tries counter, table and room orders in that sequence. Falls back to
    returning HTML when WeasyPrint is unavailable.
    """

    row = (
        await session.execute(
            select(CounterOrder.id, CounterOrder.placed_at, Counter.code)
            .join(Counter, Counter.id == CounterOrder.counter_id)
            .where(CounterOrder.id == order_id)
        )
    ).first()

    if row:
        order_id_db, placed_at, code = row
        source_type = "Counter"
        item_rows = await session.execute(
            select(
                CounterOrderItem.name_snapshot,
                CounterOrderItem.qty,
                CounterOrderItem.mods_snapshot,
            ).where(CounterOrderItem.order_id == order_id)
        )
        items = []
        for name, qty, mods in item_rows.all():
            items.append({"name": name, "qty": qty, "notes": ""})
            for mod in mods or []:
                items.append({"name": f"- {mod['label']}", "qty": qty, "notes": ""})
    else:
        row = (
            await session.execute(
                select(Order.id, Order.placed_at, Table.code)
                .join(Table, Table.id == Order.table_id)
                .where(Order.id == order_id)
            )
        ).first()
        if row:
            order_id_db, placed_at, code = row
            source_type = "Table"
            item_rows = await session.execute(
                select(
                    OrderItem.name_snapshot,
                    OrderItem.qty,
                    OrderItem.mods_snapshot,
                ).where(OrderItem.order_id == order_id)
            )
            items = []
            for name, qty, mods in item_rows.all():
                items.append({"name": name, "qty": qty, "notes": ""})
                for mod in mods or []:
                    items.append({"name": f"- {mod['label']}", "qty": qty, "notes": ""})
        else:
            row = (
                await session.execute(
                    select(RoomOrder.id, RoomOrder.placed_at, Room.code)
                    .join(Room, Room.id == RoomOrder.room_id)
                    .where(RoomOrder.id == order_id)
                )
            ).first()
            if row:
                order_id_db, placed_at, code = row
                source_type = "Room"
                item_rows = await session.execute(
                    select(
                        RoomOrderItem.name_snapshot,
                        RoomOrderItem.qty,
                        RoomOrderItem.mods_snapshot,
                    ).where(RoomOrderItem.room_order_id == order_id)
                )
                items = []
                for name, qty, mods in item_rows.all():
                    items.append({"name": name, "qty": qty, "notes": ""})
                    for mod in mods or []:
                        items.append({"name": f"- {mod['label']}", "qty": qty, "notes": ""})
            else:
                raise HTTPException(status_code=404, detail="order not found")

    kot = {
        "order_id": order_id_db,
        "placed_at": placed_at.isoformat() if placed_at else "",
        "source_type": source_type,
        "source_code": code,
        "items": items,
    }

    content, mimetype = render_template(
        "kot_80mm.html", {"kot": kot}, nonce=request.state.csp_nonce
    )
    return Response(content, media_type=mimetype)
