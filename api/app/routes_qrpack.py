"""Generate printable QR code packs for tables."""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Literal

import qrcode
from fastapi import APIRouter, HTTPException, Response

from .pdf.render import render_template
from .routes_onboarding import TENANTS

router = APIRouter()


_BLANK_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PQIv5gAAAABJRU5ErkJggg=="
)


def _qr_data_url(url: str) -> str:
    try:
        img = qrcode.make(url)
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        b64 = _BLANK_PNG
    return f"data:image/png;base64,{b64}"


@router.get("/api/outlet/{tenant_id}/qrpack.pdf")
async def qrpack_pdf(
    tenant_id: str, size: Literal["A4"] = "A4", per_page: int = 12
) -> Response:
    tenant = TENANTS.get(tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    tables = []
    for t in tenant.get("tables", []):
        url = f"https://example.com/{tenant_id}/{t['qr_token']}"
        tables.append({"label": t["label"], "qr": _qr_data_url(url)})
    content, mimetype = render_template(
        "qrpack.html",
        {"logo_url": tenant.get("profile", {}).get("logo_url"), "tables": tables, "per_page": per_page},
    )
    return Response(content, media_type=mimetype)


__all__ = ["router"]
