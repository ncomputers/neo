from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Response

from .pdf.render import render_invoice
from .routes_metrics import invoices_generated_total
from .services import billing_service

router = APIRouter()


@router.get("/invoice/{invoice_id}/pdf")
async def invoice_pdf(invoice_id: int, size: Literal["80mm", "A4"] = "80mm") -> Response:
    """Return a PDF (or HTML fallback) for ``invoice_id``."""

    items = [{"name": "Sample Item", "price": 10.0, "qty": 1}]
    invoice = billing_service.build_invoice_context(items, gst_mode="unreg")
    invoice["number"] = f"INV-{invoice_id}"
    content, mimetype = render_invoice(invoice, size=size)
    invoices_generated_total.inc()
    return Response(content, media_type=mimetype)
