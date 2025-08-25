"""Admin menu routes for managing menu items.

Provides an endpoint to toggle the out-of-stock flag for a menu item
within a tenant-specific database. Access is restricted to admin roles.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .auth import User, role_required
from .db.tenant import get_engine
from .repos_sqlalchemy.menu_repo_sql import MenuRepoSQL
from .utils.responses import ok
from .utils.audit import audit

router = APIRouter()


class OutOfStockToggle(BaseModel):
    """Payload for toggling the out-of-stock flag."""

    flag: bool


@asynccontextmanager
async def _session(tenant_id: str):
    """Yield an ``AsyncSession`` for the given ``tenant_id``."""

    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()


@router.post("/api/outlet/{tenant_id}/menu/item/{item_id}/out_of_stock")
@audit("toggle_out_of_stock")
async def toggle_out_of_stock(
    tenant_id: str,
    item_id: UUID,
    payload: OutOfStockToggle,
    request: Request,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Toggle the out-of-stock status of a menu item.

    Returns an empty payload on success.
    """

    repo = MenuRepoSQL()
    async with _session(tenant_id) as session:
        await repo.toggle_out_of_stock(session, item_id, payload.flag)
    await request.app.state.redis.delete(f"menu:{tenant_id}")
    return ok(None)


@router.delete("/api/outlet/{tenant_id}/menu/item/{item_id}")
@audit("delete_menu_item")
async def delete_menu_item(
    tenant_id: str,
    item_id: UUID,
    request: Request,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Soft delete a menu item."""
    repo = MenuRepoSQL()
    async with _session(tenant_id) as session:
        await repo.soft_delete_item(session, item_id)
    await request.app.state.redis.delete(f"menu:{tenant_id}")
    return ok(None)


@router.post("/api/outlet/{tenant_id}/menu/item/{item_id}/restore")
@audit("restore_menu_item")
async def restore_menu_item(
    tenant_id: str,
    item_id: UUID,
    request: Request,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Restore a previously deleted menu item."""
    repo = MenuRepoSQL()
    async with _session(tenant_id) as session:
        await repo.restore_item(session, item_id)
    await request.app.state.redis.delete(f"menu:{tenant_id}")
    return ok(None)
