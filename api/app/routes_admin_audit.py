from __future__ import annotations

"""Admin route for listing audit log entries."""

from fastapi import APIRouter, Depends

from .audit import Audit, SessionLocal
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
