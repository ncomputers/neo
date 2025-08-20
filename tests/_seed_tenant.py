from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from api.app.models_tenant import Category, MenuItem, Table


async def seed_minimal_menu(session: AsyncSession) -> dict:
    """Seed a minimal menu setup for tests.

    Creates one category, two items (veg and non-veg) and one table with code
    ``"T-001"``. Returns the created IDs.
    """

    category = Category(name="Default", sort=1)
    session.add(category)
    await session.flush()

    veg_item = MenuItem(
        category_id=category.id,
        name="Veg Item",
        price=100,
        is_veg=True,
    )
    non_veg_item = MenuItem(
        category_id=category.id,
        name="Non-Veg Item",
        price=150,
        is_veg=False,
    )
    session.add_all([veg_item, non_veg_item])

    table = Table(
        tenant_id=uuid.uuid4(),
        name="Table 1",
        code="T-001",
    )
    session.add(table)

    await session.commit()

    return {
        "category_id": category.id,
        "veg_item_id": veg_item.id,
        "non_veg_item_id": non_veg_item.id,
        "table_id": table.id,
    }
