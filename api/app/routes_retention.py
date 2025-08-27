from __future__ import annotations

"""Admin routes for tenant data retention."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .auth import User, role_required
from .utils.responses import ok
from .services import retention as retention_svc

router = APIRouter()


class RetentionPayload(BaseModel):
    tenant: str
    days: int


@router.post("/api/admin/retention/preview")
async def retention_preview(
    payload: RetentionPayload,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    data = await retention_svc.preview(payload.tenant, payload.days)
    return ok(data)


@router.post("/api/admin/retention/apply")
async def retention_apply(
    payload: RetentionPayload,
    user: User = Depends(role_required("super_admin")),
) -> dict:
    data = await retention_svc.apply(payload.tenant, payload.days)
    return ok(data)


__all__ = ["router"]
