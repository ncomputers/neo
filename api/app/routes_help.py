"""Serve in-app help pages rendered from Markdown."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from markdown import markdown

from .routes_onboarding import TENANTS

router = APIRouter()

DOCS = [
    ("Owner Onboarding", "OWNER_ONBOARDING.md"),
    ("Cashier & KDS Cheat Sheet", "CASHIER_KDS_CHEATSHEET.md"),
    ("Troubleshooting", "TROUBLESHOOTING.md"),
]


@router.get("/help", response_class=HTMLResponse)
async def help_center(request: Request, tenant_id: str | None = None) -> HTMLResponse:
    """Render bundled help documents with optional outlet branding."""
    docs_dir = Path(__file__).resolve().parents[2] / "docs"
    sections: list[str] = []
    for title, filename in DOCS:
        md_path = docs_dir / filename
        if not md_path.exists():
            continue
        md = md_path.read_text(encoding="utf-8")
        html = markdown(md)
        sections.append(f"<article><h2>{title}</h2>{html}</article>")

    sections.append(
        "<article><h2>Legal</h2><ul>"
        "<li><a href='/legal/subprocessors'>Subprocessors</a></li>"
        "<li><a href='/legal/sla'>Service Level Agreement</a></li>"
        "</ul></article>"
    )

    body = "".join(sections) or "<p>No help available.</p>"
    html = f"<html><head><title>Help</title></head><body>{body}</body></html>"

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
