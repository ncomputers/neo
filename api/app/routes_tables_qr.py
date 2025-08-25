from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from .auth import User, role_required
from .utils.responses import ok
from .utils.audit import audit

router = APIRouter()

# Load script module providing QR rotation logic
_spec = importlib.util.spec_from_file_location(
    "tenant_qr_tools",
    Path(__file__).resolve().parents[2] / "scripts" / "tenant_qr_tools.py",
)
_tenant_qr_tools = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_tenant_qr_tools)


@router.post("/api/outlet/{tenant}/tables/{code}/qr/rotate")
@audit("rotate_table_qr")
async def rotate_table_qr(
    tenant: str,
    code: str,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Rotate the QR token for ``code`` and return new deeplink."""

    try:
        info = await _tenant_qr_tools.regen_qr(tenant, code)
    except ValueError as exc:  # unknown table
        raise HTTPException(status_code=404, detail=str(exc))
    deeplink = f"https://example.com/{tenant}/{info['qr_token']}"
    info["deeplink"] = deeplink
    return ok(info)
