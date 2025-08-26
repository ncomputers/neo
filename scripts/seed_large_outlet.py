#!/usr/bin/env python3
"""Seed a large dataset for load testing.

This helper creates a category, thousands of menu items, hundreds of tables
and tens of thousands of orders with one line item each. It is intended for
local scale testing and inserts rows in batches for performance.

"""

from __future__ import annotations

import argparse
import asyncio
import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.db.tenant import get_tenant_session
from api.app.models_tenant import (
    Base,

    Category,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    Table,
)

DEFAULT_BATCH_SIZE = 1000


async def _seed(
    session: AsyncSession,
    *,
    items: int,
    tables: int,
    orders: int,
    batch_size: int,
) -> None:
    """Insert large volumes of menu items, tables and orders."""

    # Ensure tables exist for ad-hoc databases like SQLite.
    async with session.bind.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    category = Category(name="Load Test", sort=1)
    session.add(category)
    await session.flush()

    # Menu items
    item_ids: list[int] = []
    item_batch: list[dict[str, object]] = []
    for i in range(items):
        item_batch.append(
            {
                "category_id": category.id,
                "name": f"Item {i + 1}",
                "price": 100,
                "is_veg": False,
            }
        )
        if len(item_batch) >= batch_size:
            res = await session.execute(
                insert(MenuItem).returning(MenuItem.id), item_batch
            )
            item_ids.extend(res.scalars().all())
            item_batch.clear()
    if item_batch:
        res = await session.execute(
            insert(MenuItem).returning(MenuItem.id), item_batch
        )
        item_ids.extend(res.scalars().all())

    # Tables
    table_ids: list[uuid.UUID] = []
    table_batch: list[dict[str, object]] = []
    tenant_uuid = uuid.uuid4()
    for i in range(tables):
        table_id = uuid.uuid4()
        table_ids.append(table_id)
        table_batch.append(
            {
                "id": table_id,
                "tenant_id": tenant_uuid,
                "name": f"Table {i + 1}",
                "code": f"T-{i + 1:03d}",
                "qr_token": uuid.uuid4().hex,
            }
        )
        if len(table_batch) >= batch_size:
            await session.execute(insert(Table), table_batch)
            table_batch.clear()
    if table_batch:
        await session.execute(insert(Table), table_batch)

    # Orders and order items
    order_batch: list[dict[str, object]] = []
    order_item_batch: list[dict[str, object]] = []
    for _ in range(orders):
        table_id = random.choice(table_ids)
        order_batch.append(
            {
                "table_id": table_id,
                "status": OrderStatus.CONFIRMED,
                "placed_at": datetime.now(timezone.utc),
            }
        )
        if len(order_batch) >= batch_size:
            res = await session.execute(
                insert(Order).returning(Order.id), order_batch
            )
            order_ids = res.scalars().all()
            for order_id in order_ids:
                item_id = random.choice(item_ids)
                order_item_batch.append(
                    {
                        "order_id": order_id,
                        "item_id": item_id,
                        "name_snapshot": f"Item {item_id}",
                        "price_snapshot": 100,
                        "qty": 1,
                        "status": "SERVED",
                    }
                )
            await session.execute(insert(OrderItem), order_item_batch)
            order_batch.clear()
            order_item_batch.clear()
    if order_batch:
        res = await session.execute(insert(Order).returning(Order.id), order_batch)
        order_ids = res.scalars().all()
        for order_id in order_ids:
            item_id = random.choice(item_ids)
            order_item_batch.append(
                {
                    "order_id": order_id,
                    "item_id": item_id,
                    "name_snapshot": f"Item {item_id}",
                    "price_snapshot": 100,
                    "qty": 1,
                    "status": "SERVED",
                }
            )
        await session.execute(insert(OrderItem), order_item_batch)

    await session.commit()


async def main(
    tenant: str,
    *,
    items: int,
    tables: int,
    orders: int,
    batch_size: int,
) -> None:
    async with get_tenant_session(tenant) as session:
        await _seed(
            session,
            items=items,
            tables=tables,
            orders=orders,
            batch_size=batch_size,
        )
    print(f"Seeded {items} items, {tables} tables and {orders} orders")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed a large dataset")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument("--items", type=int, default=5000, help="Number of menu items")
    parser.add_argument("--tables", type=int, default=300, help="Number of tables")
    parser.add_argument("--orders", type=int, default=50000, help="Number of orders")
    parser.add_argument(
        "--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Bulk insert batch size"
    )
    args = parser.parse_args()
    asyncio.run(
        main(
            args.tenant,
            items=args.items,
            tables=args.tables,
            orders=args.orders,
            batch_size=args.batch_size,
        )
    )
