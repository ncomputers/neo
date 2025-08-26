from __future__ import annotations

"""Admin routes for QR pack audit logs."""

import csv
from io import StringIO

from fastapi import APIRouter, Depends, Response

from .audit import QrPackLog, SessionLocal
from .auth import User, role_required
from .utils.pagination import Pagination
from .utils.pagination import pagination as paginate
from .utils.responses import ok

router = APIRouter()


@router.get("/api/admin/qrpacks/logs")
def list_qrpack_logs(
    pack_id: str | None = None,
    requester: str | None = None,
    reason: str | None = None,
    page: Pagination = Depends(paginate),
    user: User = Depends(role_required("super_admin")),
) -> dict:
    with SessionLocal() as session:
        query = session.query(QrPackLog).order_by(QrPackLog.id.desc())
        if pack_id:
            query = query.filter(QrPackLog.pack_id == pack_id)
        if requester:
            query = query.filter(QrPackLog.requester == requester)
        if reason:
            query = query.filter(QrPackLog.reason == reason)
        if page.cursor:
            query = query.filter(QrPackLog.id < page.cursor)
        query = query.limit(page.limit)
        rows = [
            {
                "id": row.id,
                "pack_id": row.pack_id,
                "count": row.count,
                "requester": row.requester,
                "reason": row.reason,
                "created_at": row.created_at,
            }
            for row in query.all()
        ]
    return ok(rows)


@router.get("/api/admin/qrpacks/export")
def export_qrpack_logs(
    pack_id: str | None = None,
    requester: str | None = None,
    reason: str | None = None,
    user: User = Depends(role_required("super_admin")),
) -> Response:
    with SessionLocal() as session:
        query = session.query(QrPackLog).order_by(QrPackLog.id.desc())
        if pack_id:
            query = query.filter(QrPackLog.pack_id == pack_id)
        if requester:
            query = query.filter(QrPackLog.requester == requester)
        if reason:
            query = query.filter(QrPackLog.reason == reason)
        rows = query.all()
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "pack_id", "count", "requester", "reason", "created_at"])
        for row in rows:
            writer.writerow(
                [
                    row.id,
                    row.pack_id,
                    row.count,
                    row.requester,
                    row.reason,
                    row.created_at.isoformat(),
                ]
            )
    return Response(
        buf.getvalue(),
        media_type="text/csv",
        headers={"content-disposition": "attachment; filename=qrpack_logs.csv"},
    )


__all__ = ["router"]
