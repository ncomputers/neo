from __future__ import annotations

from typing import Literal

import json

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from .auth import User, role_required

router = APIRouter(prefix="/api/outlet/{tenant}/print")


class PrintNotify(BaseModel):
    order_id: int
    size: Literal["80mm"] = "80mm"


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
