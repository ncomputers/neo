"""Admin test route for printers."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

router = APIRouter()


class PrintTestPayload(BaseModel):
    printer: Literal["58mm", "80mm"]


@router.post("/admin/print/test")
async def admin_print_test(payload: PrintTestPayload, request: Request) -> PlainTextResponse:
    """Return preview text and publish a test print event."""
    timestamp = datetime.utcnow().isoformat()
    outlet = "demo"
    title = "test"
    preview = f"outlet: {outlet}\ntitle: {title}\ntimestamp: {timestamp}\n"
    redis = request.app.state.redis
    await redis.publish(f"print:test:{payload.printer}", preview)
    return PlainTextResponse(preview)
