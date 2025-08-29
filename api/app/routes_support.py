"""Support contact information and ticket submission."""

from __future__ import annotations

import re
import uuid
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from .auth import User, role_required
from .db import SessionLocal
from .models_master import FeedbackNPS, SupportMessage, SupportTicket
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
    message: str = Field(..., description="Detailed description")
    channel: str | None = None
    attachments: list[str] = Field(default_factory=list)
    includeDiagnostics: bool = False
    diagnostics: dict | None = None


class ReplyIn(BaseModel):
    message: str
    attachments: list[str] = Field(default_factory=list)


class FeedbackIn(BaseModel):
    score: int = Field(..., ge=0, le=10)
    comment: str | None = Field(default=None)
    feature_request: bool = Field(default=False)


token_re = re.compile(r"bearer\s+[A-Za-z0-9\._-]+", re.I)
utr_re = re.compile(r"\b\d{10}\b")


def _redact(data):  # pragma: no cover - simple recursion
    if isinstance(data, str):
        data = token_re.sub("[REDACTED]", data)
        data = utr_re.sub("[REDACTED]", data)
        return data
    if isinstance(data, list):
        return [_redact(v) for v in data]
    if isinstance(data, dict):
        return {k: _redact(v) for k, v in data.items()}
    return data


@router.post("/support/tickets")
@audit("support.ticket")
async def create_ticket(
    payload: TicketIn,
    request: Request,
    user: User = Depends(role_required("owner", "super_admin")),
) -> dict:
    tenant = request.headers.get("X-Tenant-ID", "unknown")
    diagnostics = _redact(payload.diagnostics) if payload.includeDiagnostics else None
    ticket = SupportTicket(
        tenant=tenant,
        subject=payload.subject,
        body=_redact(payload.message),
        screenshots=payload.attachments,
        diagnostics=diagnostics,
        channel=payload.channel,
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
            "body": payload.message,
            "errors": errors,
        },
        "ops@",
    )
    return ok({"id": ticket_id})


@router.get("/support/tickets")
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
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]
    return ok(tickets)


@router.post("/support/tickets/{ticket_id}/reply")
@audit("support.reply")
async def reply_ticket(
    ticket_id: str,
    payload: ReplyIn,
    request: Request,
    user: User = Depends(role_required("owner", "super_admin")),
) -> dict:
    with SessionLocal() as session:
        ticket = session.get(SupportTicket, uuid.UUID(ticket_id))
        if not ticket:
            return ok({"status": "not_found"})
        msg = SupportMessage(
            ticket_id=ticket.id,
            author=user.role,
            body=_redact(payload.message),
            attachments=payload.attachments,
        )
        session.add(msg)
        ticket.updated_at = func.now()
        session.commit()
    return ok({"status": "sent"})


@router.post("/support/feedback")
@audit("support.feedback")
async def submit_feedback(
    payload: FeedbackIn,
    request: Request,
    user: User = Depends(role_required("owner", "super_admin")),
) -> dict:
    tenant = request.headers.get("X-Tenant-ID", "unknown")
    fb = FeedbackNPS(
        tenant=tenant,
        user=user.username,
        score=payload.score,
        comment=payload.comment,
        feature_request=payload.feature_request,
    )
    with SessionLocal() as session:
        session.add(fb)
        session.commit()
    return ok({"status": "thanks"})
