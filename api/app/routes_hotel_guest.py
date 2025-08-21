from __future__ import annotations

"""Guest-facing hotel room service routes backed by tenant databases."""

from typing import AsyncGenerator, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db.tenant import get_engine
from .models_tenant import MenuItem, Room, RoomOrder, RoomOrderItem
from .repos_sqlalchemy.menu_repo_sql import MenuRepoSQL
from .services import notifications
from .utils.responses import ok

router = APIRouter(prefix="/h")


class OrderLine(BaseModel):
    """Single line item for a room service order."""

    item_id: int
    qty: int


class OrderPayload(BaseModel):
    """Payload containing the items being ordered."""

    items: List[OrderLine]


async def get_tenant_id() -> str:
    """Resolve the tenant identifier for the current request.

    This is a placeholder implementation and will be replaced when tenant
    resolution is wired in.
    """

    return "demo"  # TODO: derive from request context


async def get_tenant_session(
    tenant_id: str = Depends(get_tenant_id),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an ``AsyncSession`` bound to the tenant's database."""

    engine = get_engine(tenant_id)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with sessionmaker() as session:
        yield session


@router.get("/{room_token}/menu")
async def fetch_menu(
    room_token: str,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    """Return menu categories and items for hotel guests."""

    repo = MenuRepoSQL()
    categories = await repo.list_categories(session)
    items = await repo.list_items(session)
    return ok({"categories": categories, "items": items})


@router.post("/{room_token}/order")
async def create_order(
    room_token: str,
    payload: OrderPayload,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    """Create a new room service order for ``room_token``."""

    lines = [line.model_dump() for line in payload.items]

    room_id = await session.scalar(select(Room.id).where(Room.code == room_token))
    if room_id is None:
        raise HTTPException(status_code=404, detail="room not found")

    order = RoomOrder(room_id=room_id, status="NEW", placed_at=func.now())
    session.add(order)
    await session.flush()

    item_ids = [l["item_id"] for l in lines]
    if item_ids:
        result = await session.execute(
            select(MenuItem.id, MenuItem.name, MenuItem.price).where(MenuItem.id.in_(item_ids))
        )
        items = {row.id: row for row in result}
    else:
        items = {}

    for line in lines:
        data = items.get(line["item_id"])
        if data is None:
            raise HTTPException(status_code=400, detail="item not found")
        session.add(
            RoomOrderItem(
                room_order_id=order.id,
                item_id=line["item_id"],
                name_snapshot=data.name,
                price_snapshot=data.price,
                qty=line["qty"],
                status="NEW",
            )
        )

    await session.commit()
    return ok({"order_id": order.id})


@router.post("/{room_token}/request/cleaning")
async def request_cleaning(
    room_token: str,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Request housekeeping for the given room."""

    await notifications.enqueue(tenant_id, "housekeeping.requested", {"room_token": room_token})
    return ok({"requested": True})
