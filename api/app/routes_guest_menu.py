# routes_guest_menu.py

"""Guest-facing menu routes backed by the tenant database."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from .db.replica import read_only
from .i18n import get_msg, resolve_lang
from .menu.dietary import filter_items
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
@read_only
async def fetch_menu(
    table_token: str,
    request: Request,
    response: Response,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    """Return menu categories and items for guests with caching and ETag support."""
    repo = MenuRepoSQL()
    etag = await repo.menu_etag(session)
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})
    cache_key = f"menu:{tenant_id}"
    redis = request.app.state.redis
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
    else:
        categories = await repo.list_categories(session)
        items = await repo.list_items(session)
        data = {"categories": categories, "items": items}
        await redis.set(cache_key, json.dumps(data), ex=60)
    items = data["items"]
    if filter:
        items = filter_items(items, filter)
    data["items"] = items

    lang = resolve_lang(accept_language)
    resp_data = {**data, "items": items}
    resp_data["labels"] = {
        name: get_msg(lang, f"labels.{name}")
        for name in ("menu", "order", "pay", "get_bill")
    }
    response.headers["ETag"] = etag
    return ok(resp_data)
