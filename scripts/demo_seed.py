#!/usr/bin/env python3
"""Seed demo data including menu items, tables and images.

This helper populates a tenant database with a small menu and six dining
tables. Placeholder images are saved to ``api/app/static/images``. Pass
``--reset`` to purge existing categories, items and tables before seeding.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.db.tenant import get_tenant_session
from api.app.models_tenant import Category, MenuItem, Table

IMAGE_DIR = Path("api/app/static/images")

# Simple 1x1 transparent PNG
PNG_DATA = bytes.fromhex(
    "89504E470D0A1A0A0000000D4948445200000001000000010802000000907753DE"
    "0000000A49444154789C63600000020001840A2F0000000049454E44AE426082"
)

MENU_ITEMS = [
    ("Idli", 30, True),
    ("Dosa", 50, True),
    ("Tea", 15, False),
]


async def _reset(session: AsyncSession) -> None:
    """Remove existing menu items, categories and tables."""

    for model in (MenuItem, Category, Table):
        await session.execute(delete(model))
    await session.commit()


def _create_image(name: str) -> str:
    """Create a placeholder image file and return its path."""

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    path = IMAGE_DIR / f"{name.lower().replace(' ', '_')}.png"
    if not path.exists():
        path.write_bytes(PNG_DATA)
    return str(path)


async def _seed(session: AsyncSession) -> dict[str, object]:
    """Insert demo data and return created identifiers."""

    category = Category(name="Demo", sort=1)
    session.add(category)
    await session.flush()

    items = []
    for name, price, is_veg in MENU_ITEMS:
        image_path = _create_image(name)
        item = MenuItem(category_id=category.id, name=name, price=price, is_veg=is_veg)
        session.add(item)
        await session.flush()
        items.append({"id": item.id, "name": name, "image": image_path})

    tables = []
    for i in range(1, 7):
        table = Table(
            tenant_id=uuid.uuid4(),
            name=f"Table {i}",
            code=f"T-{i:03d}",
            qr_token=uuid.uuid4().hex,
        )
        session.add(table)
        tables.append(
            {"id": str(table.id), "code": table.code, "qr_token": table.qr_token}
        )

    await session.commit()
    return {"category_id": category.id, "items": items, "tables": tables}


async def main(tenant: str, reset: bool) -> None:
    async with get_tenant_session(tenant) as session:
        if reset:
            await _reset(session)
        data = await _seed(session)
    print(json.dumps(data))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo tenant data")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument(
        "--reset", action="store_true", help="Purge existing data before seeding"
    )
    args = parser.parse_args()
    asyncio.run(main(args.tenant, args.reset))
