"""Send WhatsApp status notifications."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .db import SessionLocal
from .flags import get as flag_get
from .models_tenant import AuditTenant
from .providers import whatsapp_stub
from .utils.responses import ok

ALLOWED_STATUSES = {"accepted", "ready", "out_for_delivery"}

router = APIRouter()


class StatusUpdate(BaseModel):
    phone: str
    order_id: int
    status: str


def _status_ok(status: str) -> bool:
    return status in ALLOWED_STATUSES


async def _send_with_backoff(event: str, payload: dict, target: str) -> str:
    delay = 0.1
    for attempt in range(3):
        try:
            msg_id = whatsapp_stub.send(event, payload, target)
            return str(msg_id) if msg_id is not None else str(event)
        except Exception as exc:  # pragma: no cover - defensive
            status = getattr(exc, "status_code", None)
            if status is None:
                response = getattr(exc, "response", None)
                if response is not None:
                    status = getattr(response, "status_code", None)
            if status and status >= 500 and attempt < 2:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError("send failed")


@router.post("/api/outlet/{tenant}/whatsapp/status")
async def whatsapp_status(tenant: str, update: StatusUpdate) -> dict:
    if not flag_get("wa_enabled"):
        return ok({"sent": False})
    if not _status_ok(update.status):
        raise HTTPException(status_code=400, detail="unsupported status")
    payload = {"order_id": update.order_id, "status": update.status}
    msg_id = await _send_with_backoff(update.status, payload, update.phone)
    with SessionLocal() as session:
        session.add(
            AuditTenant(
                actor="system",
                action="whatsapp_status",
                meta={"tenant": tenant, "msg_id": msg_id},
            )
        )
        session.commit()
    return ok({"sent": True, "msg_id": msg_id})
