from __future__ import annotations

"""Endpoints for table housekeeping and cleaning workflows."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func

from .auth import User, role_required
from .db import SessionLocal
from .events import event_bus
from .models_tenant import Table
from .utils.responses import ok


router = APIRouter(prefix="/api/outlet/{tenant}/housekeeping")


@router.post("/table/{table_id}/start_clean")
async def start_clean(
    tenant: str,
    table_id: str,
    user: User = Depends(role_required("cleaner", "super_admin")),
) -> dict:
    """Mark ``table_id`` as awaiting cleaning."""

    try:
        tid = uuid.UUID(table_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid table id") from exc

    with SessionLocal() as session:
        table = session.get(Table, tid)
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
        table.state = "PENDING_CLEANING"
        session.commit()
        session.refresh(table)
        return ok({"table_id": table_id, "state": table.state})


@router.post("/table/{table_id}/ready")
async def mark_ready(
    tenant: str,
    table_id: str,
    user: User = Depends(role_required("cleaner", "super_admin")),
) -> dict:
    """Mark cleaning complete and reopen the table."""

    await event_bus.publish("table.cleaned", {"table_id": table_id})
    try:
        tid = uuid.UUID(table_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid table id") from exc

    with SessionLocal() as session:
        table = session.get(Table, tid)
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
        table.state = "AVAILABLE"
        table.last_cleaned_at = func.now()
        session.commit()
        session.refresh(table)
        return ok({"table_id": table_id, "state": table.state})
