from __future__ import annotations

"""Guest-facing hotel room routes."""

import asyncio
import hashlib
import json

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, validator
from sqlalchemy import func

from .db import SessionLocal
from .i18n import get_msg, resolve_lang
from .models_tenant import (
    Category,
    MenuItem,
    NotificationOutbox,
    Room,
    RoomOrder,
    RoomOrderItem,
)
from .utils.i18n import get_text
from .utils.responses import ok

router = APIRouter(prefix="/h")


class OrderLine(BaseModel):
    item_id: int | str
    qty: int

    @validator("item_id", pre=True)
    def _coerce_item_id(cls, v: int | str) -> int:  # noqa: N805 - pydantic validator
        try:
            return int(v)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError("item_id must be an integer") from exc

    @validator("qty")
    def _validate_qty(cls, v: int) -> int:  # noqa: N805 - pydantic validator
        if v <= 0:
            raise ValueError("qty must be greater than 0")
        return v


class OrderPayload(BaseModel):
    items: list[OrderLine]


@router.get("/{room_token}/menu")
def fetch_menu(
    room_token: str,
    request: Request,
    response: Response,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> dict:
    """Return menu categories and items for hotel rooms with ETag and caching."""

    with SessionLocal() as session:
        cat_ts = session.query(func.max(Category.updated_at)).scalar()
        item_ts = session.query(func.max(MenuItem.updated_at)).scalar()
    etag = hashlib.sha1(
        f"{cat_ts}{item_ts}".encode(), usedforsecurity=False
    ).hexdigest()
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})

    cache_key = "menu:default"
    redis = request.app.state.redis
    cached = asyncio.run(redis.get(cache_key))
    if cached:
        data = json.loads(cached)
    else:
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
                for i in session.query(MenuItem).filter(
                    MenuItem.out_of_stock.is_(False)
                )
            ]
        data = {"categories": categories, "items": items}
        asyncio.run(redis.set(cache_key, json.dumps(data), ex=60))
    lang = resolve_lang(accept_language)
    for item in data["items"]:
        item["name"] = get_text(item.get("name"), lang, item.get("name_i18n"))
        if item.get("description") or item.get("desc_i18n"):
            item["description"] = get_text(
                item.get("description"), lang, item.get("desc_i18n")
            )
    data["labels"] = {
        name: get_msg(lang, f"labels.{name}")
        for name in ("menu", "order", "pay", "get_bill")
    }
    response.headers["ETag"] = etag
    return ok(data)


@router.post("/{room_token}/order")
def create_order(room_token: str, payload: OrderPayload) -> dict:
    lines = [{"item_id": line.item_id, "qty": line.qty} for line in payload.items]
    with SessionLocal() as session:
        room = session.query(Room).filter_by(code=room_token).one_or_none()
        if room is None:
            raise HTTPException(status_code=404, detail="room not found")
        order = RoomOrder(room_id=room.id, status="NEW", placed_at=func.now())
        session.add(order)
        session.flush()
        item_ids = [line["item_id"] for line in lines]
        items = {
            i.id: i for i in session.query(MenuItem).filter(MenuItem.id.in_(item_ids))
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
