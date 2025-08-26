from __future__ import annotations

"""Routes exposing a simple integration marketplace with webhook probes."""

from typing import Any, Dict

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

TENANT_INTEGRATIONS: Dict[str, Dict[str, Dict[str, Any]]] = {}


class ConnectPayload(BaseModel):
    type: str
    url: HttpUrl | None = None
    key: str | None = None


@router.get("/api/outlet/{tenant}/integrations/marketplace")
async def list_marketplace(
    tenant: str, user: User = Depends(role_required("super_admin"))
) -> dict:
    configs = TENANT_INTEGRATIONS.get(tenant, {})
    items = [
        {
            "type": key,
            "name": cfg["name"],
            "sample_payload": cfg["sample_payload"],
            "connected": key in configs,
        }
        for key, cfg in INTEGRATIONS.items()
    ]
    return ok(items)


@router.post("/api/outlet/{tenant}/integrations/connect")
async def connect_integration(
    tenant: str,
    payload: ConnectPayload,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    cfg = INTEGRATIONS.get(payload.type)
    if not cfg:
        raise HTTPException(status_code=404, detail="UNKNOWN_INTEGRATION")
    dest = payload.url or payload.key
    if dest is None:
        raise HTTPException(status_code=400, detail="MISSING_DESTINATION")
    probe_report = None
    if payload.url:
        probe_report = await probe_webhook(str(payload.url))
        warnings = set(probe_report.get("warnings", []))
        if "tls_self_signed" in warnings:
            raise HTTPException(
                status_code=400,
                detail="Webhook has self-signed TLS certificate",
            )
        if "slow" in warnings:
            raise HTTPException(
                status_code=400,
                detail="Webhook responded too slowly",
            )
    TENANT_INTEGRATIONS.setdefault(tenant, {})[payload.type] = {
        "url": str(payload.url) if payload.url else None,
        "key": payload.key,
    }
    return ok(
        {
            "type": payload.type,
            "config": TENANT_INTEGRATIONS[tenant][payload.type],
            "probe": probe_report,
        }
    )


__all__ = ["router", "INTEGRATIONS", "TENANT_INTEGRATIONS"]
