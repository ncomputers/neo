# routes_guest_menu.py

"""Guest-facing menu routes backed by the tenant database."""

from __future__ import annotations

import hashlib
import json

import httpx
from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings

from .db.replica import read_only
from .i18n import get_msg, resolve_lang
from .menu.dietary import filter_items
from .middlewares.sanitize import sanitize_html
from .repos_sqlalchemy.menu_repo_sql import MenuRepoSQL
from .utils.i18n import get_text
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
    filter_str = request.query_params.get("filter")
    if filter_str:
        items = filter_items(items, filter_str)
    lang = resolve_lang(accept_language)
    items_out = []
    for item in items:
        item_out = {
            "id": item["id"],
            "out_of_stock": bool(item.get("out_of_stock", False)),
        }
        if "name" in item and item["name"] is not None:
            item_out["name"] = get_text(item.get("name"), lang, item.get("name_i18n"))
        elif item.get("name_i18n"):
            item_out["name"] = get_text(item.get("name"), lang, item.get("name_i18n"))
        if item.get("description") or item.get("desc_i18n"):
            desc = get_text(item.get("description"), lang, item.get("desc_i18n"))
            if desc:
                item_out["description"] = sanitize_html(desc)
        items_out.append(item_out)
    data["items"] = items_out

    resp_data = {**data, "items": items_out}
    resp_data["labels"] = {
        name: get_msg(lang, f"labels.{name}")
        for name in ("menu", "order", "pay", "get_bill")
    }
    settings = get_settings()
    if settings.ab_tests_enabled:
        variant = request.cookies.get("ab_menu")
        if variant not in {"A", "B"}:
            bucket = (
                int(
                    hashlib.md5(
                        table_token.encode(), usedforsecurity=False
                    ).hexdigest(),
                    16,
                )
                % 2
            )
            variant = "B" if bucket else "A"
            response.set_cookie("ab_menu", variant, path="/")
        resp_data["ab_variant"] = variant
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                await client.post(
                    f"{settings.proxy_url}/analytics/ab",
                    json={
                        "tenant": tenant_id,
                        "test": "menu",
                        "variant": variant,
                        "event": "exposure",
                    },
                )
        except Exception:
            pass
    response.headers["ETag"] = etag
    return ok(resp_data)
