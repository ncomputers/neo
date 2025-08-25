from __future__ import annotations

"""Routes for scheduling maintenance windows per tenant."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import User, role_required
from .db import SessionLocal
from .models_master import Tenant
from .utils.audit import audit
from .utils.responses import ok


class MaintenancePayload(BaseModel):
    """Payload for scheduling maintenance."""

    until: datetime
    note: str | None = None


router = APIRouter()


@router.post("/api/outlet/{tenant}/maintenance/schedule")
@audit("schedule_maintenance")
async def schedule_maintenance(
    tenant: str,
    payload: MaintenancePayload,
    user: User = Depends(role_required("super_admin", "outlet_admin")),
) -> dict:
    """Set ``maintenance_until`` for ``tenant``."""

    tenant_uuid = uuid.UUID(tenant)
    with SessionLocal() as session:
        row = session.get(Tenant, tenant_uuid)
        if row is None:
            raise HTTPException(status_code=404, detail="Tenant not found")
        row.maintenance_until = payload.until.replace(tzinfo=None)
        session.commit()
        session.refresh(row)
        return ok({"maintenance_until": row.maintenance_until.isoformat()})
