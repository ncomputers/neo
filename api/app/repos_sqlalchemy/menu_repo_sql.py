"""SQLAlchemy implementation of menu repository using tenant models."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models_tenant import Category, MenuItem
from ..repos.menu_repo import MenuRepo


class MenuRepoSQL(MenuRepo):
    """Concrete MenuRepo using SQLAlchemy with an AsyncSession."""

    async def list_categories(self, session: AsyncSession) -> list[dict]:
        """Return all menu categories ordered by the sort field."""
        result = await session.execute(select(Category).order_by(Category.sort))
        return [
            {"id": c.id, "name": c.name, "sort": c.sort} for c in result.scalars().all()
        ]

    async def list_items(
        self, session: AsyncSession, include_hidden: bool = False
    ) -> list[dict]:
        """Return menu items, optionally including those marked out of stock."""
        stmt = select(MenuItem)
        if not include_hidden:
            stmt = stmt.where(MenuItem.out_of_stock.is_(False))
        result = await session.execute(stmt)
        items = []
        for item in result.scalars().all():
            items.append(
                {
                    "id": item.id,
                    "category_id": item.category_id,
                    "name": item.name,
                    "price": float(item.price),
                    "is_veg": item.is_veg,
                    "gst_rate": (
                        float(item.gst_rate) if item.gst_rate is not None else None
                    ),
                    "hsn_sac": item.hsn_sac,
                    "show_fssai": item.show_fssai,
                    "out_of_stock": item.out_of_stock,
                }
            )
        return items

    async def toggle_out_of_stock(
        self, session: AsyncSession, item_id: UUID, flag: bool
    ) -> None:
        """Set the out-of-stock flag for a menu item."""
        stmt = update(MenuItem).where(MenuItem.id == item_id).values(out_of_stock=flag)
        await session.execute(stmt)
        await session.commit()
