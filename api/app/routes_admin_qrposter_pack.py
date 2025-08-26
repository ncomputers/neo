"""Admin endpoint to download QR poster packs."""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Literal
from zipfile import ZipFile

import qrcode
from fastapi import APIRouter, HTTPException, Response

from .pdf.render import render_template
from .routes_onboarding import TENANTS

router = APIRouter()

_BLANK_PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PQIv5gAAAABJRU5ErkJggg=="


def _qr_data_url(url: str) -> str:
    try:
        img = qrcode.make(url)
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        b64 = _BLANK_PNG
    return f"data:image/png;base64,{b64}"


@router.get("/api/admin/outlets/{tenant_id}/qrposters.zip")
async def qr_poster_pack(
    tenant_id: str, size: Literal["A4", "A5"] = "A4"
) -> Response:
    tenant = TENANTS.get(tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    buffer = BytesIO()
    with ZipFile(buffer, "w") as zf:
        for t in tenant.get("tables", []):
            url = f"https://example.com/{tenant_id}/{t['qr_token']}"
            qr = _qr_data_url(url)
            content, _ = render_template(
                "qrposter.html",
                {
                    "label": t.get("label", t["code"]),
                    "qr": qr,
                    "size": size,
                    "instructions": "Scan to order & pay",
                },
            )
            zf.writestr(f"{t['code']}.pdf", content)
    buffer.seek(0)
    headers = {
        "content-disposition": f"attachment; filename={tenant_id}_qrposters.zip"
    }
    return Response(buffer.getvalue(), media_type="application/zip", headers=headers)


__all__ = ["router"]
