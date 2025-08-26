"""Admin test route for printers."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from .render_text_image import render_text_image

router = APIRouter()


class PrintTestPayload(BaseModel):
    printer: Literal["58mm", "80mm"]


class PrintTestResponse(BaseModel):
    preview: str
    image: str


@router.post("/admin/print/test", response_model=PrintTestResponse)
async def admin_print_test(
    payload: PrintTestPayload, request: Request
) -> PrintTestResponse:
    """Return preview text and publish a test print event."""
    timestamp = datetime.now(timezone.utc).isoformat()
    outlet = "demo"
    title = request.app.title
    preview = f"outlet: {outlet}\ntitle: {title}\ntimestamp: {timestamp}\n"
    png_bytes = render_text_image(preview)
    image_b64 = base64.b64encode(png_bytes).decode()
    redis = request.app.state.redis
    await redis.publish(f"print:test:{payload.printer}", preview)
    return PrintTestResponse(preview=preview, image=image_b64)
