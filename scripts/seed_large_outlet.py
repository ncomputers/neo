#!/usr/bin/env python3
"""Bulk seed a tenant with large datasets for local scale testing.

This helper inserts many tables, menu items and orders using SQLAlchemy bulk
operations. It is intended only for development environments to quickly
produce data volumes that mimic a busy outlet.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.db.tenant import get_tenant_session
from api.app.models_tenant import (
    Category,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    Table,
)


async def _seed(
    session: AsyncSession, tables: int, items: int, orders: int, days: int
) -> None:
    """Populate ``session`` with synthetic tables, items and orders."""

    # Create a single category for all menu items
    category = Category(name="Bulk", sort=1)
    session.add(category)
    await session.flush()

    # Generate menu items and collect their ids for snapshots
    item_payload = []
    for i in range(1, items + 1):
        item_payload.append(
            {
                "category_id": category.id,
                "name": f"Item {i}",
                "price": (i % 100) + 1,
                "is_veg": i % 2 == 0,
            }
        )
    result = await session.execute(
        insert(MenuItem).returning(MenuItem.id, MenuItem.name, MenuItem.price),
        item_payload,
    )
    items_info = {row.id: (row.name, row.price) for row in result.mappings().all()}

    # Tables are keyed by UUID so we generate ids upfront
    table_payload: list[dict] = []
    table_ids: list[uuid.UUID] = []
    for i in range(1, tables + 1):
        table_id = uuid.uuid4()
        table_ids.append(table_id)
        table_payload.append(
            {
                "id": table_id,
                "tenant_id": uuid.uuid4(),
                "name": f"Table {i}",
                "code": f"T-{i:03d}",
                "qr_token": uuid.uuid4().hex,
            }
        )
    await session.execute(insert(Table), table_payload)

    # Orders with a single line item each spread over ``days`` days
    now = datetime.utcnow()
    order_rows: list[dict] = []
    chosen_items: list[int] = []
    for _ in range(orders):
        table_id = random.choice(table_ids)
        item_id = random.choice(list(items_info))
        chosen_items.append(item_id)
        placed_at = now - timedelta(days=random.randrange(days))
        order_rows.append(
            {
                "table_id": table_id,
                "status": OrderStatus.SERVED,
                "placed_at": placed_at,
                "accepted_at": placed_at,
            }
        )
    result = await session.execute(insert(Order).returning(Order.id), order_rows)
    order_ids = result.scalars().all()

    order_item_rows = []
    for order_id, item_id in zip(order_ids, chosen_items):
        name, price = items_info[item_id]
        order_item_rows.append(
            {
                "order_id": order_id,
                "item_id": item_id,
                "name_snapshot": name,
                "price_snapshot": price,
                "qty": 1,
                "status": "served",
                "mods_snapshot": [],
            }
        )
    await session.execute(insert(OrderItem), order_item_rows)
    await session.commit()


async def main(tenant: str, tables: int, items: int, orders: int, days: int) -> None:
    async with get_tenant_session(tenant) as session:
        await _seed(session, tables, items, orders, days)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed a tenant with a large synthetic dataset"
    )
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument(
        "--tables", type=int, default=300, help="Number of tables to create"
    )
    parser.add_argument(
        "--items", type=int, default=5000, help="Number of menu items to create"
    )
    parser.add_argument(
        "--orders", type=int, default=50000, help="Number of orders to create"
    )
    parser.add_argument(
        "--days", type=int, default=60, help="Spread orders across past days"
    )
    args = parser.parse_args()
    asyncio.run(main(args.tenant, args.tables, args.items, args.orders, args.days))
