"""Repository helpers for counter takeaway orders."""

from __future__ import annotations

from typing import List

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils import invoice_counter

from ..models_tenant import (
    MenuItem,
    Counter,
    CounterOrder,
    CounterOrderItem,
    CounterOrderStatus,
    Invoice,
)


async def create_order(
    session: AsyncSession, counter_token: str, lines: List[dict]
) -> int:
    """Create a counter order for ``counter_token`` with ``lines``."""

    counter_id = await session.scalar(
        select(Counter.id).where(Counter.qr_token == counter_token)
    )
    if counter_id is None:  # pragma: no cover - defensive check
        raise ValueError(f"counter {counter_token!r} not found")

    order = CounterOrder(
        counter_id=counter_id,
        status=CounterOrderStatus.PLACED.value,
        placed_at=func.now(),
    )
    session.add(order)
    await session.flush()

    item_ids = [int(l["item_id"]) for l in lines]
    if item_ids:
        result = await session.execute(
            select(MenuItem.id, MenuItem.name, MenuItem.price).where(
                MenuItem.id.in_(item_ids)
            )
        )
        items = {row.id: row for row in result}
    else:  # pragma: no cover - empty order
        items = {}

    for line in lines:
        key = int(line["item_id"])
        data = items.get(key)
        if data is None:  # pragma: no cover - menu item missing
            raise ValueError(f"menu item {line['item_id']!r} not found")
        session.add(
            CounterOrderItem(
                order_id=order.id,
                item_id=key,
                name_snapshot=data.name,
                price_snapshot=data.price,
                qty=line["qty"],
            )
        )

    await session.commit()
    return order.id


async def update_status(
    session: AsyncSession, order_id: int, new_status: str
) -> int | None:
    """Update ``order_id`` to ``new_status``. Return invoice id if generated."""

    values = {"status": new_status}
    if new_status == CounterOrderStatus.DELIVERED.value:
        values["delivered_at"] = func.now()
    await session.execute(
        update(CounterOrder).where(CounterOrder.id == order_id).values(**values)
    )

    invoice_id = None
    if new_status == CounterOrderStatus.DELIVERED.value:
        result = await session.execute(
            select(
                CounterOrderItem.name_snapshot,
                CounterOrderItem.price_snapshot,
                CounterOrderItem.qty,
            ).where(CounterOrderItem.order_id == order_id)
        )
        items = result.all()
        total = sum(row.price_snapshot * row.qty for row in items)
        number = await invoice_counter.next_invoice_number(session, "80mm")
        invoice = Invoice(
            order_group_id=order_id,
            number=number,
            bill_json={
                "items": [
                    {
                        "name": row.name_snapshot,
                        "qty": row.qty,
                        "price": float(row.price_snapshot),
                    }
                    for row in items
                ],
                "total": float(total),
            },
            total=total,
        )
        session.add(invoice)
        await session.flush()
        invoice_id = invoice.id

    await session.commit()
    return invoice_id
