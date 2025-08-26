"""Admin routes for probing webhook destinations."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, HttpUrl

from .auth import User, role_required
from .utils.responses import ok
from .utils.webhook_probe import probe_webhook

router = APIRouter()

PROBE_REPORTS: dict[str, dict] = {}


class ProbePayload(BaseModel):
    url: HttpUrl


@router.post("/admin/webhooks/probe")
async def admin_webhook_probe(
    payload: ProbePayload, user: User = Depends(role_required("super_admin"))
) -> dict:
    """Probe ``payload.url`` and store a report for later inspection."""
    report = await probe_webhook(str(payload.url))
    PROBE_REPORTS[str(payload.url)] = report
    return ok(report)
