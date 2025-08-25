"""Routes for managing table floor-map positions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func

from .auth import User, role_required
from .db import SessionLocal
from .models_tenant import Table
from .utils.audit import audit
from .utils.responses import ok


class TablePosition(BaseModel):
    """Coordinates for placing a table on a floor map."""

    x: int
    y: int
    label: str | None = None


router = APIRouter()


class TableCreate(BaseModel):
    """Payload for creating a new table."""

    code: str


@router.post("/api/outlet/{tenant}/tables")
@audit("create_table")
async def create_table(
    tenant: str,
    payload: TableCreate,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Create a table placeholder.

    Actual persistence is handled elsewhere; this endpoint exists for limit
    checks in tests.
    """

    return ok({"code": payload.code})


@router.post("/api/outlet/{tenant}/tables/{table_id}/position")
@audit("set_table_position")
async def set_table_position(
    tenant: str,
    table_id: uuid.UUID,
    pos: TablePosition,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Persist positional metadata for a table."""

    with SessionLocal() as session:
        table = session.get(Table, table_id)
        if table is None or table.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Table not found")
        table.pos_x = pos.x
        table.pos_y = pos.y
        table.label = pos.label
        session.commit()
        session.refresh(table)
        return ok(
            {
                "id": str(table.id),
                "x": table.pos_x,
                "y": table.pos_y,
                "label": table.label,
            }
        )


@router.get("/api/outlet/{tenant}/tables/map")
@audit("get_table_map")
async def get_table_map(tenant: str, include_deleted: bool = False) -> dict:
    """Return coordinates and states for all tables."""

    with SessionLocal() as session:
        query = session.query(Table)
        if not include_deleted:
            query = query.filter(Table.deleted_at.is_(None))
        records = query.all()
        data = [
            {
                "id": str(t.id),
                "code": t.code,
                "label": t.label,
                "x": t.pos_x,
                "y": t.pos_y,
                "state": t.state,
            }
            for t in records
        ]
    return ok(data)


@router.patch("/api/outlet/{tenant}/tables/{code}/delete")
@audit("table.soft_delete")
async def delete_table(
    tenant: str,
    code: str,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Soft delete a table."""
    with SessionLocal() as session:
        table = (
            session.query(Table)
            .filter_by(tenant_id=uuid.UUID(tenant), code=code)
            .one_or_none()
        )
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
        table.deleted_at = func.now()
        session.commit()
    return ok(None)


@router.post("/api/outlet/{tenant}/tables/{code}/restore")
@audit("table.restore")
async def restore_table(
    tenant: str,
    code: str,
    user: User = Depends(role_required("super_admin", "outlet_admin", "manager")),
) -> dict:
    """Restore a previously deleted table."""
    with SessionLocal() as session:
        table = (
            session.query(Table)
            .filter_by(tenant_id=uuid.UUID(tenant), code=code)
            .one_or_none()
        )
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
        table.deleted_at = None
        session.commit()
    return ok(None)
