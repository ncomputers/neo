from __future__ import annotations

"""Admin route for listing audit log entries."""

import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse

from .audit import Audit, SessionLocal
from .auth import User, role_required
from .utils.pagination import Pagination
from .utils.pagination import pagination as paginate
from .utils.responses import ok

router = APIRouter(prefix="/admin/audit")


@router.get("")
def list_audit_logs(
    page: Pagination = Depends(paginate),
    actor: Optional[str] = Query(None),
    event: Optional[str] = Query(None),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    format: Optional[str] = Query(None),
    user: User = Depends(role_required("owner", "super_admin")),
) -> Response:
    """Return audit log entries with optional filters and CSV export."""

    with SessionLocal() as session:
        query = session.query(Audit).order_by(Audit.id.desc())
        if actor:
            query = query.filter(Audit.actor == actor)
        if event:
            query = query.filter(Audit.action.like(f"{event}%"))
        if start:
            query = query.filter(Audit.created_at >= datetime.fromisoformat(start))
        if end:
            query = query.filter(Audit.created_at <= datetime.fromisoformat(end))
        if page.cursor:
            query = query.filter(Audit.id < page.cursor)
        query = query.limit(page.limit)
        rows = [
            {
                "id": row.id,
                "actor": row.actor,
                "action": row.action,
                "entity": row.entity,
                "created_at": row.created_at.isoformat(),
            }
            for row in query.all()
        ]

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "actor", "action", "entity", "created_at"])
        for r in rows:
            writer.writerow([r["id"], r["actor"], r["action"], r["entity"], r["created_at"]])
        return Response(output.getvalue(), media_type="text/csv")

    return JSONResponse(ok(rows))
