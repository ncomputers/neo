"""SQLAlchemy-backed repository helpers for orders.

These helpers implement basic order workflows without any side effects
beyond database mutations. They operate on ``AsyncSession`` instances and
use snapshotting for order items so that historical prices and names are
retained even if the menu changes later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List
import json
from datetime import datetime, timezone

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain import OrderStatus
from ..models_tenant import MenuItem, Order, OrderItem, Table
from . import ema_repo_sql
from ..services import ema


@dataclass
class OrderSummary:
    """Lightweight representation of an order used by ``list_active``."""

    id: int
    table_code: str
    status: str


async def create_order(
    session: AsyncSession, table_code: str, lines: List[dict]
) -> int:
    """Create a new order for ``table_code`` with ``lines``.

    Each entry in ``lines`` must contain ``item_id`` and ``qty``. The current
    menu name and price for each item are snapshotted into ``order_items``.
    Returns the newly created order's identifier.
    """

    table_id = await session.scalar(select(Table.id).where(Table.code == table_code))
    if table_id is None:  # pragma: no cover - defensive check
        raise ValueError(f"table {table_code!r} not found")

    order = Order(table_id=table_id, status=OrderStatus.PLACED.value)
    session.add(order)
    await session.flush()  # obtain order.id

    item_ids = [l["item_id"] for l in lines]
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
        data = items.get(line["item_id"])
        if data is None:  # pragma: no cover - menu item missing
            raise ValueError(f"menu item {line['item_id']!r} not found")
        session.add(
            OrderItem(
                order_id=order.id,
                item_id=line["item_id"],
                name_snapshot=data.name,
                price_snapshot=data.price,
                qty=line["qty"],
                status=OrderStatus.PLACED.value,
            )
        )

    await session.commit()
    return order.id


async def list_active(session: AsyncSession) -> List[OrderSummary]:
    """Return all active orders as ``OrderSummary`` objects."""

    active_statuses = [
        OrderStatus.PLACED.value,
        OrderStatus.ACCEPTED.value,
        OrderStatus.IN_PROGRESS.value,
        OrderStatus.READY.value,
        OrderStatus.HOLD.value,
    ]

    result = await session.execute(
        select(Order.id, Table.code, Order.status)
        .join(Table, Order.table_id == Table.id)
        .where(Order.status.in_(active_statuses))
    )

    return [
        OrderSummary(id=row.id, table_code=row.code, status=row.status)
        for row in result
    ]


async def update_status(
    session: AsyncSession, order_id: int, new_status: str
) -> str | None:
    """Persist a new status for ``order_id`` and timestamp it.

    Returns the table code for the updated order if available.
    """

    field_map = {
        OrderStatus.PLACED.value: "placed_at",
        OrderStatus.ACCEPTED.value: "accepted_at",
        OrderStatus.READY.value: "ready_at",
        OrderStatus.SERVED.value: "served_at",
    }
    values = {"status": new_status}
    field = field_map.get(new_status)
    if field:
        values[field] = func.now()
    await session.execute(update(Order).where(Order.id == order_id).values(**values))
    await session.commit()

    result = await session.execute(
        select(Table.code, Order.accepted_at)
        .join(Order, Order.table_id == Table.id)
        .where(Order.id == order_id)
    )
    row = result.one_or_none()
    if row is None:
        return None

    table_code, accepted_at = row
    if new_status not in {
        OrderStatus.IN_PROGRESS.value,
        OrderStatus.READY.value,
        OrderStatus.SERVED.value,
    }:
        return table_code
    now = datetime.now(timezone.utc)
    elapsed = (now - accepted_at).total_seconds() if accepted_at else 0.0

    current = await ema_repo_sql.load(session)
    ema_val = current[1] if current else 0.0
    eta_seconds = ema.eta([], ema_val) - elapsed
    if new_status in {OrderStatus.READY.value, OrderStatus.SERVED.value}:
        eta_seconds = 0.0
    else:
        eta_seconds = max(eta_seconds, 0.0)

    from ..main import redis_client  # lazy import to avoid circular deps

    await redis_client.publish(
        f"rt:update:{table_code}",
        json.dumps(
            {
                "order_id": str(order_id),
                "status": new_status,
                "eta_secs": eta_seconds,
            }
        ),
    )
    return table_code


async def add_round(
    session: AsyncSession, order_id: int, lines: Iterable[dict]
) -> None:
    """Append additional ``lines`` to an existing order.

    ``lines`` has the same structure as for :func:`create_order`.
    """

    item_ids = [l["item_id"] for l in lines]
    if not item_ids:
        return

    result = await session.execute(
        select(MenuItem.id, MenuItem.name, MenuItem.price).where(
            MenuItem.id.in_(item_ids)
        )
    )
    items = {row.id: row for row in result}

    for line in lines:
        data = items.get(line["item_id"])
        if data is None:  # pragma: no cover - menu item missing
            raise ValueError(f"menu item {line['item_id']!r} not found")
        session.add(
            OrderItem(
                order_id=order_id,
                item_id=line["item_id"],
                name_snapshot=data.name,
                price_snapshot=data.price,
                qty=line["qty"],
                status=OrderStatus.PLACED.value,
            )
        )

    await session.commit()
