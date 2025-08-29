from __future__ import annotations

"""Admin route for listing audit log entries."""

import csv
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Response

from .audit import Audit, SessionLocal
from .auth import User, role_required
from .utils.responses import ok

router = APIRouter()


@router.get('/admin/audit')
def list_audit_logs(
    actor: str | None = Query(None),
    event: str | None = Query(None),
    date: str | None = Query(None),
    format: str | None = Query(None),
    user: User = Depends(role_required('super_admin')),
):
    with SessionLocal() as session:
        query = session.query(Audit).order_by(Audit.id.desc())
        if actor:
            query = query.filter(Audit.actor == actor)
        if event:
            query = query.filter(Audit.action == event)
        if date:
            start = datetime.fromisoformat(date)
            end = start + timedelta(days=1)
            query = query.filter(Audit.created_at >= start, Audit.created_at < end)
        rows = [
            {
                'id': row.id,
                'actor': row.actor,
                'action': row.action,
                'entity': row.entity,
                'created_at': row.created_at,
            }
            for row in query.limit(100).all()
        ]
    if format == 'csv':
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['id', 'actor', 'action', 'entity', 'created_at'])
        for r in rows:
            writer.writerow([r['id'], r['actor'], r['action'], r['entity'], r['created_at']])
        return Response(
            buffer.getvalue(),
            media_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename=audit.csv'},
        )
    return ok(rows)


__all__ = ['router']
