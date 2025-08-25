from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from .security import blocklist
from .staff_auth import role_required
from .utils.responses import ok
from .utils.audit import audit
from .audit import log_event

router = APIRouter()


class UnblockIPPayload(BaseModel):
    ip: str


@router.post("/api/outlet/{tenant}/security/unblock_ip")
@audit("unblock_ip")
async def unblock_ip(
    tenant: str,
    payload: UnblockIPPayload,
    request: Request,
    staff=Depends(role_required("admin")),
) -> dict:
    redis = request.app.state.redis
    await blocklist.clear_ip(redis, tenant, payload.ip)
    log_event(str(staff.staff_id), "unblock_ip", f"{tenant}:{payload.ip}")
    return ok(True)


__all__ = ["router"]
