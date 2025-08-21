"""Invoice PDF rendering route."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Response

from .pdf.render import render_invoice
from .routes_metrics import invoices_generated_total

router = APIRouter()


@router.get("/invoice/{invoice_id}/pdf")
async def invoice_pdf(invoice_id: int, size: Literal["80mm", "A4"] = "80mm") -> Response:
    """Return a PDF (or HTML fallback) for ``invoice_id``.

    A real implementation would fetch the invoice JSON from persistence.
    For now, a placeholder invoice is rendered.
    """
    invoice = {
        "number": f"INV-{invoice_id}",
        "items": [
            {"name": "Sample Item", "price": 10.0, "qty": 1},
        ],
        "total": 10.0,
    }
    content, mimetype = render_invoice(invoice, size=size)
    invoices_generated_total.inc()
    return Response(content, media_type=mimetype)
