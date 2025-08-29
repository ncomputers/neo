from __future__ import annotations

"""Admin route for listing audit log entries."""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select

from .audit import Audit, AuditMaster, SessionLocal
from .auth import User, role_required
from .utils.pagination import Pagination
from .utils.pagination import pagination as paginate
from .utils.responses import ok

router = APIRouter()


@router.get("/api/admin/audit/logs")
def list_audit_logs(
    page: Pagination = Depends(paginate),
    user: User = Depends(role_required("super_admin")),
) -> dict:
    with SessionLocal() as session:
        query = session.query(Audit).order_by(Audit.id.desc())
        if page.cursor:
            query = query.filter(Audit.id < page.cursor)
        query = query.limit(page.limit)
        rows = [
            {
                "id": row.id,
                "actor": row.actor,
                "action": row.action,
                "entity": row.entity,
                "created_at": row.created_at,
            }
            for row in query.all()
        ]
    return ok(rows)


@router.get("/admin/audit")
def owner_audit(
    actor: str | None = None,
    event: str | None = None,
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None, alias="to"),
    format: str | None = None,
    user: User = Depends(role_required("owner", "super_admin")),
):
    with SessionLocal() as session:
        stmt = select(AuditMaster).order_by(AuditMaster.created_at.desc())
        if actor:
            stmt = stmt.where(AuditMaster.actor == actor)
        if event:
            stmt = stmt.where(AuditMaster.action == event)
        if from_:
            stmt = stmt.where(AuditMaster.created_at >= datetime.fromisoformat(from_))
        if to:
            stmt = stmt.where(AuditMaster.created_at <= datetime.fromisoformat(to))
        rows = session.execute(stmt).scalars().all()
        data = [
            {
                "id": r.id,
                "actor": r.actor,
                "action": r.action,
                "entity": r.entity,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "actor", "action", "entity", "created_at"])
        for r in data:
            writer.writerow(
                [r["id"], r["actor"], r["action"], r["entity"], r["created_at"]]
            )
        return Response(buf.getvalue(), media_type="text/csv")
    return ok(data)
