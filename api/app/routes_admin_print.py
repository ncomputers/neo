"""Admin routes for testing ESC/POS templates."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from .printing.escpos_presets import TEMPLATE_MAP, render_preset

router = APIRouter()


class PreviewPayload(BaseModel):
    size: str = "80mm"
    vars: dict = {}


@router.post("/admin/print/test")
def admin_print_test(payload: PreviewPayload) -> PlainTextResponse:
    """Render an ESC/POS preset for preview."""
    if payload.size not in TEMPLATE_MAP:
        raise HTTPException(status_code=400, detail="unsupported size")
    text = render_preset(payload.size, payload.vars)
    return PlainTextResponse(text)
