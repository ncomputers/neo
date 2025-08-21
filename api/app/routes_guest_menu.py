# routes_guest_menu.py

"""Guest-facing menu routes backed by the tenant database."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .repos_sqlalchemy.menu_repo_sql import MenuRepoSQL
from .utils.responses import ok

router = APIRouter()


async def get_tenant_id(table_token: str) -> str:
    """Return the tenant identifier for ``table_token``.

    This is a placeholder dependency to be implemented with real lookup logic.
    """
    raise NotImplementedError


async def get_tenant_session(tenant_id: str) -> AsyncSession:
    """Return an ``AsyncSession`` bound to ``tenant_id``'s database.

    This stub will be replaced with logic that opens a tenant-specific session.
    """
    raise NotImplementedError


@router.get("/g/{table_token}/menu")
async def fetch_menu(
    table_token: str,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    """Return menu categories and items for guests."""
    repo = MenuRepoSQL()
    categories = await repo.list_categories(session)
    items = await repo.list_items(session)
    return ok({"categories": categories, "items": items})
