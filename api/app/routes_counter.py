"""Routes for takeaway counter orders using a single QR."""

from __future__ import annotations

from typing import AsyncGenerator, List

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.tenant import get_engine
from .utils.responses import ok
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


async def get_tenant_id() -> str:
    """Resolve tenant identifier for guest requests."""

    return "demo"  # placeholder until tenant resolution is wired


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
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    """Return menu categories and items for the counter."""

    repo = MenuRepoSQL()
    categories = await repo.list_categories(session)
    items = await repo.list_items(session)
    return ok({"categories": categories, "items": items})


@router.post("/{counter_token}/order")
async def create_order(
    counter_token: str,
    payload: OrderPayload,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
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
async def update_status(
    tenant_id: str,
    order_id: int,
    payload: StatusPayload,
    session: AsyncSession = Depends(get_session_from_path),
) -> dict:
    """Update status and generate an 80mm invoice when delivered."""

    invoice_id = await counter_orders_repo_sql.update_status(
        session, order_id, payload.status
    )
    return ok({"invoice_id": invoice_id})
