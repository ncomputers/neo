from __future__ import annotations

"""Admin routes for closing and restoring tenants."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from .auth import User, role_required
from .db import SessionLocal
from .models_master import Tenant
from .utils.audit import audit
from .utils.responses import ok

router = APIRouter()


@router.post("/api/outlet/{tenant}/close")
@audit("close_tenant")
async def close_tenant(
    tenant: str, user: User = Depends(role_required("super_admin", "outlet_admin"))
) -> dict:
    """Mark a tenant as closed and schedule data purge."""

    tenant_uuid = uuid.UUID(tenant)
    with SessionLocal() as session:
        row = session.get(Tenant, tenant_uuid)
        if row is None:
            raise HTTPException(status_code=404, detail="Tenant not found")
        now = datetime.utcnow()
        row.closed_at = now
        row.purge_at = now + timedelta(days=90)
        row.status = "closed"
        session.commit()
        session.refresh(row)
        return ok(
            {
                "closed_at": row.closed_at.isoformat(),
                "purge_at": row.purge_at.isoformat(),
            }
        )


@router.post("/api/admin/tenants/{tenant}/restore")
@audit("restore_tenant")
async def restore_tenant(
    tenant: str, user: User = Depends(role_required("super_admin"))
) -> dict:
    """Reactivate a closed tenant if still within the purge window."""

    tenant_uuid = uuid.UUID(tenant)
    with SessionLocal() as session:
        row = session.get(Tenant, tenant_uuid)
        if row is None or row.closed_at is None:
            raise HTTPException(status_code=404, detail="Tenant not found")
        if row.purge_at and row.purge_at <= datetime.utcnow():
            raise HTTPException(status_code=410, detail="Purge window elapsed")
        row.closed_at = None
        row.purge_at = None
        row.status = "active"
        session.commit()
        session.refresh(row)
        return ok({"status": row.status})
