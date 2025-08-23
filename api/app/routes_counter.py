"""Routes for takeaway counter orders using a single QR."""

from __future__ import annotations

from typing import AsyncGenerator, List

from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import json

from .auth import User, role_required
from .db.tenant import get_engine
from .deps.tenant import get_tenant_id
from .utils.responses import ok
from .i18n import resolve_lang, get_msg
from .utils.audit import audit
from .repos_sqlalchemy.menu_repo_sql import MenuRepoSQL
from .repos_sqlalchemy import counter_orders_repo_sql

router = APIRouter(prefix="/c")
router_admin = APIRouter(prefix="/api/outlet/{tenant_id}/counters")


class OrderLine(BaseModel):
    item_id: str
    qty: int


class OrderPayload(BaseModel):
    items: List[OrderLine]


class StatusPayload(BaseModel):
    status: str


async def get_tenant_session(
    tenant_id: str = Depends(get_tenant_id),
) -> AsyncGenerator[AsyncSession, None]:
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with sessionmaker() as session:
        yield session


async def get_session_from_path(
    tenant_id: str,
) -> AsyncGenerator[AsyncSession, None]:
    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with sessionmaker() as session:
        yield session


@router.get("/{counter_token}/menu")
async def fetch_menu(
    counter_token: str,
    request: Request,
    response: Response,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    """Return menu categories and items for the counter."""

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
    lang = resolve_lang(accept_language)
    data["labels"] = {
        name: get_msg(lang, f"labels.{name}")
        for name in ("menu", "order", "pay", "get_bill")
    }
    response.headers["ETag"] = etag
    return ok(data)


@router.post("/{counter_token}/order")
async def create_order(
    counter_token: str,
    payload: OrderPayload,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    lines = [line.model_dump() for line in payload.items]
    try:
        order_id = await counter_orders_repo_sql.create_order(
            session, counter_token, lines
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok({"order_id": order_id})


@router_admin.post("/{order_id}/status")
@audit("update_counter_status")
async def update_status(
    tenant_id: str,
    order_id: int,
    payload: StatusPayload,
    session: AsyncSession = Depends(get_session_from_path),
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Update status and generate an 80mm invoice when delivered."""

    invoice_id = await counter_orders_repo_sql.update_status(
        session, order_id, payload.status
    )
    return ok({"invoice_id": invoice_id})
