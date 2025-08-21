from __future__ import annotations

"""Guest-facing hotel room routes."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import func

from .db import SessionLocal
from .deps.flags import require_flag
from .models_tenant import (
    Category,
    MenuItem,
    Room,
    RoomOrder,
    RoomOrderItem,
    NotificationOutbox,
)
from .utils.responses import ok

router = APIRouter(prefix="/h", dependencies=[Depends(require_flag("enable_hotel"))])


class OrderLine(BaseModel):
    item_id: int
    qty: int


class OrderPayload(BaseModel):
    items: list[OrderLine]


@router.get("/{room_token}/menu")
def fetch_menu(room_token: str) -> dict:
    with SessionLocal() as session:
        categories = [
            {"id": c.id, "name": c.name, "sort": c.sort}
            for c in session.query(Category).order_by(Category.sort)
        ]
        items = [
            {
                "id": i.id,
                "category_id": i.category_id,
                "name": i.name,
                "price": float(i.price),
                "is_veg": i.is_veg,
                "gst_rate": float(i.gst_rate) if i.gst_rate is not None else None,
                "hsn_sac": i.hsn_sac,
                "show_fssai": i.show_fssai,
                "out_of_stock": i.out_of_stock,
            }
            for i in session.query(MenuItem).filter(MenuItem.out_of_stock.is_(False))
        ]
    return ok({"categories": categories, "items": items})


@router.post("/{room_token}/order")
def create_order(room_token: str, payload: OrderPayload) -> dict:
    lines = [line.model_dump() for line in payload.items]
    with SessionLocal() as session:
        room = session.query(Room).filter_by(code=room_token).one_or_none()
        if room is None:
            raise HTTPException(status_code=404, detail="room not found")
        order = RoomOrder(room_id=room.id, status="NEW", placed_at=func.now())
        session.add(order)
        session.flush()
        item_ids = [l["item_id"] for l in lines]
        items = {
            i.id: i
            for i in session.query(MenuItem).filter(MenuItem.id.in_(item_ids))
        }
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
        session.commit()
        return ok({"order_id": order.id})


@router.post("/{room_token}/request/cleaning")
async def request_cleaning(room_token: str) -> dict:
    with SessionLocal() as session:
        session.add(
            NotificationOutbox(
                event="housekeeping.requested",
                payload={"room_code": room_token},
                channel="internal",
                target="housekeeping",
            )
        )
        session.commit()
    return ok({"requested": True})
