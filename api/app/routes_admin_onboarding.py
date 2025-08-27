from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/admin/onboarding", response_class=HTMLResponse)
async def admin_onboarding() -> HTMLResponse:
    """Render the owner onboarding wizard template."""
    tpl = Path(__file__).resolve().parents[2] / "templates" / "onboarding.html"
    html = tpl.read_text(encoding="utf-8")
    return HTMLResponse(html)


__all__ = ["router"]
