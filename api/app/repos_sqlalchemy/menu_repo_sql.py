"""SQLAlchemy implementation of menu repository using tenant models."""

from __future__ import annotations

from uuid import UUID
import hashlib

from sqlalchemy import select, update, func, insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models_tenant import Category, MenuItem, TenantMeta
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
        """Set the out-of-stock flag for a menu item and bump menu version."""
        stmt = (
            update(MenuItem)
            .where(MenuItem.id == item_id)
            .values(out_of_stock=flag, updated_at=func.now())
        )
        await session.execute(stmt)
        await self._bump_menu_version(session)
        await session.commit()

    async def _bump_menu_version(self, session: AsyncSession) -> None:
        """Increment the tenant's menu version."""
        stmt = (
            update(TenantMeta)
            .values(menu_version=TenantMeta.menu_version + 1, updated_at=func.now())
        )
        result = await session.execute(stmt)
        if result.rowcount == 0:
            await session.execute(
                insert(TenantMeta).values(menu_version=1, updated_at=func.now())
            )

    async def menu_etag(self, session: AsyncSession) -> str:
        """Return a hash derived from the tenant's menu version."""
        version = await session.scalar(select(TenantMeta.menu_version)) or 0
        payload = str(version).encode()
        return hashlib.sha1(payload).hexdigest()
