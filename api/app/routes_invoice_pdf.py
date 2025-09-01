from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request, Response

from config import get_settings

from .pdf.render import render_invoice
from .routes_metrics import invoices_generated_total
from .services import billing_service

router = APIRouter()


@router.get("/invoice/{invoice_id}/pdf")
async def invoice_pdf(
    invoice_id: int, request: Request, size: Literal["80mm", "A4"] = "80mm"
) -> Response:
    """Return a PDF (or HTML fallback) for ``invoice_id``."""

    items = [{"name": "Sample Item", "price": 10.0, "qty": 1}]
    settings = get_settings()
    invoice = billing_service.build_invoice_context(
        items,
        gst_mode="unreg",
        happy_hour_windows=settings.happy_hour_windows,
    )
    invoice["number"] = f"INV-{invoice_id}"
    content, mimetype = render_invoice(
        invoice, size=size, nonce=request.state.csp_nonce
    )
    invoices_generated_total.inc()
    response = Response(content, media_type=mimetype)
    response.headers["Content-Type"] = mimetype
    return response
