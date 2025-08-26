"""Support contact information and ticket submission."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from .auth import User, role_required
from .db import SessionLocal
from .models_master import SupportTicket
from .providers import email_stub
from .utils.audit import audit
from .utils.responses import ok

router = APIRouter()


@router.get("/support/contact")
async def support_contact() -> dict:
    """Return support contact details."""
    return {
        "email": "support@example.com",
        "phone": "+1-800-555-0199",
        "hours": "09:00-18:00 IST",
        "docs_url": "https://docs.example.com",
        "privacy_url": "/legal/privacy",
        "terms_url": "/legal/terms",
    }


class TicketIn(BaseModel):
    subject: str = Field(..., description="Short summary")
    body: str = Field(..., description="Detailed description")
    screenshots: list[str] = Field(default_factory=list)


@router.post("/support/ticket")
@audit("support.ticket")
async def create_ticket(
    payload: TicketIn,
    request: Request,
    user: User = Depends(role_required("owner", "super_admin")),
) -> dict:
    tenant = request.headers.get("X-Tenant-ID", "unknown")
    ticket = SupportTicket(
        tenant=tenant,
        subject=payload.subject,
        body=payload.body,
        screenshots=payload.screenshots,
    )
    with SessionLocal() as session:
        session.add(ticket)
        session.commit()
        ticket_id = str(ticket.id)
    errors = getattr(request.app.state, "last_errors", [])
    email_stub.send(
        "support_ticket",
        {
            "subject": f"[{tenant}] {payload.subject}",
            "body": payload.body,
            "errors": errors,
        },
        "ops@",
    )
    return ok({"id": ticket_id})


@router.get("/support/ticket")
async def list_my_tickets(
    request: Request,
    user: User = Depends(role_required("owner", "super_admin")),
) -> dict:
    tenant = request.headers.get("X-Tenant-ID", "unknown")
    with SessionLocal() as session:
        rows = (
            session.execute(select(SupportTicket).where(SupportTicket.tenant == tenant))
            .scalars()
            .all()
        )
        tickets = [
            {
                "id": str(r.id),
                "subject": r.subject,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    return ok(tickets)
