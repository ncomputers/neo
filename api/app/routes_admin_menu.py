"""Admin menu routes for managing menu items.

Provides an endpoint to toggle the out-of-stock flag for a menu item
within a tenant-specific database. Access is restricted to admin roles.
"""

from __future__ import annotations

import csv
import io
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .auth import User, role_required
from .db.tenant import get_engine
from .models_tenant import MenuItem, TenantMeta
from .repos_sqlalchemy.menu_repo_sql import MenuRepoSQL
from .utils.audit import audit
from .utils.responses import ok

router = APIRouter()


class ItemCreate(BaseModel):
    """Minimal payload for creating a menu item."""

    name: str


@router.post("/api/outlet/{tenant_id}/menu/items")
@audit("create_menu_item")
async def create_menu_item(
    tenant_id: str,
    payload: ItemCreate,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Create a menu item placeholder used for limit checks."""

    return ok({"name": payload.name})


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


@router.get("/api/outlet/{tenant_id}/menu/items")
@audit("list_menu_items")
async def list_menu_items(
    tenant_id: str,
    include_deleted: bool = False,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Return menu items for admins with optional deleted records."""

    repo = MenuRepoSQL()
    async with _session(tenant_id) as session:
        items = await repo.list_items(
            session, include_hidden=True, include_deleted=include_deleted
        )
    return ok(items)


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


@router.patch("/api/outlet/{tenant_id}/menu/items/{item_id}/delete")
@audit("item.soft_delete")
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
        item = await session.get(MenuItem, item_id)
    await request.app.state.redis.delete(f"menu:{tenant_id}")
    return ok({"id": str(item.id), "name": item.name, "deleted_at": item.deleted_at})


@router.post("/api/outlet/{tenant_id}/menu/items/{item_id}/restore")
@audit("item.restore")
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
        item = await session.get(MenuItem, item_id)
    await request.app.state.redis.delete(f"menu:{tenant_id}")
    return ok({"id": str(item.id), "name": item.name, "deleted_at": item.deleted_at})


@router.post("/api/outlet/{tenant_id}/menu/i18n/import")
@audit("menu_i18n_import")
async def import_menu_i18n(
    tenant_id: str,
    file: UploadFile = File(...),
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    data = (await file.read()).decode("utf-8")
    reader = csv.DictReader(io.StringIO(data))
    async with _session(tenant_id) as session:
        enabled = await session.scalar(select(TenantMeta.enabled_langs)) or ["en"]
        for row in reader:
            lang = row.get("lang")
            if lang not in enabled:
                raise HTTPException(status_code=400, detail="unsupported language")
            item = await session.get(MenuItem, int(row["item_id"]))
            if not item:
                continue
            ni = item.name_i18n or {}
            di = item.desc_i18n or {}
            if row.get("name"):
                ni[lang] = row["name"]
            if row.get("description"):
                di[lang] = row["description"]
            item.name_i18n = ni
            item.desc_i18n = di
        await session.commit()
    return ok({"status": "imported"})


@router.get("/api/outlet/{tenant_id}/menu/i18n/export")
@audit("menu_i18n_export")
async def export_menu_i18n(
    tenant_id: str,
    langs: str,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> Response:
    lang_list = [code for code in langs.split(",") if code]
    async with _session(tenant_id) as session:
        enabled = await session.scalar(select(TenantMeta.enabled_langs)) or ["en"]
        for code in lang_list:
            if code not in enabled:
                raise HTTPException(status_code=400, detail="unsupported language")
        result = await session.execute(select(MenuItem))
        rows = []
        for item in result.scalars().all():
            for code in lang_list:
                name = (item.name_i18n or {}).get(code)
                desc = (item.desc_i18n or {}).get(code)
                if name or desc:
                    rows.append(
                        {
                            "item_id": item.id,
                            "lang": code,
                            "name": name,
                            "description": desc,
                        }
                    )
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=["item_id", "lang", "name", "description"]
    )
    writer.writeheader()
    writer.writerows(rows)
    return Response(output.getvalue(), media_type="text/csv")
