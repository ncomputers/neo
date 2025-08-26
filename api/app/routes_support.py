"""Support contact information and ticket submission."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from .auth import User, role_required
from .db import SessionLocal
from .models_master import SupportTicket
from .providers import email_stub
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
        "ops@example.com",
    )
    return ok({"id": ticket_id})
