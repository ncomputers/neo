"""Serve legal policy pages."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from .routes_onboarding import TENANTS

router = APIRouter()


@router.get("/legal/{page}", response_class=HTMLResponse)
async def legal_page(
    page: str, request: Request, tenant_id: str | None = None
) -> HTMLResponse:
    """Return the named legal page with optional outlet branding."""
    file_path = (
        Path(__file__).resolve().parents[2] / "static" / "legal" / f"{page}.html"
    )
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="legal page not found")

    html = file_path.read_text(encoding="utf-8")
    tenant_id = tenant_id or request.headers.get("x-tenant-id")
    tenant = TENANTS.get(tenant_id) if tenant_id else None
    profile = tenant.get("profile", {}) if tenant else {}
    name = profile.get("name", "")
    logo_url = profile.get("logo_url")
    branding = ""
    if name or logo_url:
        branding = '<div class="brand">'
        if logo_url:
            branding += f"<img src='{logo_url}' alt='logo' style='max-height:40px;'>"
        if name:
            branding += f"<strong>{name}</strong>"
        branding += "</div>"
        html = html.replace("<body>", f"<body>{branding}", 1)
    return HTMLResponse(html)


__all__ = ["router"]
