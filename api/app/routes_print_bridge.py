from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from .auth import User, role_required

router = APIRouter(prefix="/api/outlet/{tenant}/print")


class PrintNotify(BaseModel):
    order_id: int
    size: Literal["80mm"] = "80mm"


class PrintStatus(BaseModel):
    stale: bool
    queue: int


@router.post("/notify", status_code=204)
async def notify_print(
    tenant: str,
    payload: PrintNotify,
    request: Request,
    user: User = Depends(role_required("super_admin", "outlet_admin", "kitchen")),
) -> Response:
    """Publish a KOT print event for ``tenant``."""
    redis = request.app.state.redis
    payload_json = json.dumps(payload.model_dump(), separators=(",", ":"))
    await redis.publish(f"print:kot:{tenant}", payload_json)
    return Response(status_code=204)


@router.get("/status", response_model=PrintStatus)
async def printer_status(tenant: str, request: Request) -> PrintStatus:
    """Return printer agent heartbeat status and retry queue length."""
    redis = request.app.state.redis
    hb_key = f"print:hb:{tenant}"
    q_key = f"print:retry:{tenant}"
    last = await redis.get(hb_key)
    queue_len = await redis.llen(q_key)
    stale = True
    if last:
        try:
            last_dt = datetime.fromisoformat(last.decode())
            stale = (datetime.now(timezone.utc) - last_dt).total_seconds() > 60
        except ValueError:  # pragma: no cover - bad timestamp
            stale = True
    return PrintStatus(stale=stale, queue=queue_len)
