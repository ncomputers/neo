"""Admin routes for viewing support tickets."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from .auth import User, role_required
from .db import SessionLocal
from .models_master import SupportTicket
from .utils.responses import ok

router = APIRouter()


@router.get("/admin/support")
async def list_tickets(
    user: User = Depends(role_required("super_admin")),
) -> dict:
    """List all support tickets with their status."""
    with SessionLocal() as session:
        rows = session.execute(select(SupportTicket)).scalars().all()
        tickets = [
            {
                "id": str(r.id),
                "tenant": r.tenant,
                "subject": r.subject,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    return ok(tickets)
