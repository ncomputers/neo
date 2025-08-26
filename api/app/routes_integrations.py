from __future__ import annotations

"""Routes for listing webhook integration stubs and probing destinations."""

from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

from .auth import User, role_required
from .utils.responses import ok
from .utils.webhook_probe import probe_webhook

router = APIRouter()

INTEGRATIONS: Dict[str, Dict[str, Any]] = {
    "google_sheets": {
        "name": "Google Sheets",
        "sample_payload": {"event": "row.append", "data": {"cells": ["A", "B"]}},
    },
    "slack": {
        "name": "Slack",
        "sample_payload": {"text": "Hello from Neo"},
    },
    "zoho_books": {
        "name": "Zoho Books",
        "sample_payload": {"event": "invoice.paid"},
    },
}


class ProbePayload(BaseModel):
    url: HttpUrl


@router.get("/admin/integrations")
async def list_integrations(
    user: User = Depends(role_required("super_admin")),
) -> dict:
    items = [
        {
            "type": key,
            "name": cfg["name"],
            "sample_payload": cfg["sample_payload"],
        }
        for key, cfg in INTEGRATIONS.items()
    ]
    return ok(items)


@router.post("/admin/integrations/{kind}/probe")
async def probe_integration(
    kind: str,
    payload: ProbePayload,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    cfg = INTEGRATIONS.get(kind)
    if not cfg:
        raise HTTPException(status_code=404, detail="UNKNOWN_INTEGRATION")
    report = await probe_webhook(str(payload.url))
    sample_status: int | None = None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(str(payload.url), json=cfg["sample_payload"])
            sample_status = resp.status_code
    except httpx.HTTPError:
        sample_status = None
    return ok({"probe": report, "sample_status": sample_status})
