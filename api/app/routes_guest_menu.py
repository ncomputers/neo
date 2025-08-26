# routes_guest_menu.py

"""Guest-facing menu routes backed by the tenant database."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from .db.replica import read_only
from .i18n import get_msg, resolve_lang
from .repos_sqlalchemy.menu_repo_sql import MenuRepoSQL
from .utils.responses import ok

router = APIRouter()


def _apply_filters(items: list[dict], filter_str: str) -> list[dict]:
    """Filter ``items`` based on a comma-separated ``filter_str``."""
    positives: dict[str, set[str]] = {}
    negatives: dict[str, set[str]] = {}
    for term in filter_str.split(","):
        term = term.strip()
        if not term:
            continue
        negate = term.startswith("-")
        if negate:
            term = term[1:]
        if ":" not in term:
            continue
        key, value = term.split(":", 1)
        key = key.lower()
        value = value.lower()
        if key == "allergen":
            key = "allergens"
        target = negatives if negate else positives
        target.setdefault(key, set()).add(value)

    def matches(item: dict) -> bool:
        for key, vals in positives.items():
            field_vals = [v.lower() for v in item.get(key, [])]
            if not all(v in field_vals for v in vals):
                return False
        for key, vals in negatives.items():
            field_vals = [v.lower() for v in item.get(key, [])]
            if any(v in field_vals for v in vals):
                return False
        return True

    return [item for item in items if matches(item)]


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
    filter: str | None = None,
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
        for term in filter.split(","):
            term = term.strip()
            if not term:
                continue
            neg = term.startswith("-")
            term = term[1:] if neg else term
            if ":" not in term:
                continue
            key, value = term.split(":", 1)
            field = "allergens" if key == "allergen" else key
            if neg:
                items = [i for i in items if value not in (i.get(field) or [])]
            else:
                items = [i for i in items if value in (i.get(field) or [])]
    data["items"] = items

    lang = resolve_lang(accept_language)
    resp_data = {**data, "items": items}
    resp_data["labels"] = {
        name: get_msg(lang, f"labels.{name}")
        for name in ("menu", "order", "pay", "get_bill")
    }
    response.headers["ETag"] = etag
    return ok(resp_data)
