from __future__ import annotations

import base64
from io import BytesIO
import importlib.util
from pathlib import Path

import qrcode
from fastapi import APIRouter, Depends, HTTPException

from .auth import User, role_required
from .utils.responses import ok
from .utils.audit import audit

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


# Load script module providing QR rotation logic
_spec = importlib.util.spec_from_file_location(
    "tenant_qr_tools",
    Path(__file__).resolve().parents[2] / "scripts" / "tenant_qr_tools.py",
)
_tenant_qr_tools = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_tenant_qr_tools)


@router.post("/api/outlet/{tenant}/tables/{code}/qr/rotate")
@audit("qr_rotate")
async def rotate_table_qr(
    tenant: str,
    code: str,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Rotate the QR token for ``code`` and return deeplink and QR data URL."""

    try:
        info = await _tenant_qr_tools.regen_qr(tenant, code)
    except ValueError as exc:  # unknown table
        raise HTTPException(status_code=404, detail=str(exc))
    qr_token = info["qr_token"]
    deeplink = f"https://example.com/{tenant}/{qr_token}"
    return ok({
        "deeplink": deeplink,
        "qr_png_data_url": _qr_data_url(deeplink),
    })


__all__ = ["router"]
