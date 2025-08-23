from __future__ import annotations

"""Web Push subscription endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

from .utils.responses import ok
from .services import push


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscription(BaseModel):
    endpoint: str
    keys: PushKeys


router = APIRouter()


@router.post("/api/outlet/{tenant}/push/subscribe")
async def subscribe(tenant: str, table: str, sub: PushSubscription) -> dict:
    """Store a Web Push ``subscription`` for ``tenant`` and ``table``."""
    await push.save_subscription(tenant, table, sub.model_dump())
    return ok({"status": "subscribed"})
