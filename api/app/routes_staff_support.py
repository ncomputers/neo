from __future__ import annotations

import datetime
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from .auth import User, role_required
from .db import SessionLocal
from .models_master import SupportMessage, SupportTicket
from .providers import email_stub
from .utils.responses import ok

router = APIRouter()


@router.get("/staff/support")
async def staff_list_tickets(
    status: str | None = None,
    tenant: str | None = None,
    date: str | None = None,
    user: User = Depends(role_required("super_admin", "support")),
) -> dict:
    with SessionLocal() as session:
        query = select(SupportTicket)
        if status:
            query = query.where(SupportTicket.status == status)
        if tenant:
            query = query.where(SupportTicket.tenant == tenant)
        if date:
            try:
                d = datetime.date.fromisoformat(date)
                query = query.where(func.date(SupportTicket.created_at) == d)
            except ValueError:
                pass
        rows = session.execute(query).scalars().all()
        tickets = [
            {
                "id": str(r.id),
                "subject": r.subject,
                "status": r.status,
                "tenant": r.tenant,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]
    return ok(tickets)


@router.get("/staff/support/{ticket_id}")
async def staff_get_ticket(
    ticket_id: str,
    user: User = Depends(role_required("super_admin", "support")),
) -> dict:
    with SessionLocal() as session:
        ticket = session.get(SupportTicket, uuid.UUID(ticket_id))
        if not ticket:
            return ok(None)
        msgs = (
            session.execute(
                select(SupportMessage).where(SupportMessage.ticket_id == ticket.id)
            )
            .scalars()
            .all()
        )
        messages = [
            {
                "id": str(m.id),
                "author": m.author,
                "body": m.body,
                "attachments": m.attachments,
                "internal": m.internal,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ]
        data = {
            "id": str(ticket.id),
            "subject": ticket.subject,
            "status": ticket.status,
            "tenant": ticket.tenant,
            "messages": messages,
        }
    return ok(data)


class StaffReplyIn(BaseModel):
    message: str
    attachments: list[str] = Field(default_factory=list)
    internal: bool = False


@router.post("/staff/support/{ticket_id}/reply")
async def staff_reply_ticket(
    ticket_id: str,
    payload: StaffReplyIn,
    user: User = Depends(role_required("super_admin", "support")),
) -> dict:
    with SessionLocal() as session:
        ticket = session.get(SupportTicket, uuid.UUID(ticket_id))
        if not ticket:
            return ok({"status": "not_found"})
        msg = SupportMessage(
            ticket_id=ticket.id,
            author=user.role,
            body=payload.message,
            attachments=payload.attachments,
            internal=payload.internal,
        )
        session.add(msg)
        ticket.updated_at = func.now()
        session.commit()
    email_stub.send(
        "support.email_agent_reply",
        {"subject": ticket.subject, "body": payload.message},
        "ops@",
    )
    return ok({"status": "sent"})


@router.post("/staff/support/{ticket_id}/close")
async def staff_close_ticket(
    ticket_id: str,
    user: User = Depends(role_required("super_admin", "support")),
) -> dict:
    with SessionLocal() as session:
        ticket = session.get(SupportTicket, uuid.UUID(ticket_id))
        if not ticket:
            return ok({"status": "not_found"})
        ticket.status = "closed"
        ticket.updated_at = func.now()
        session.commit()
    return ok({"status": "closed"})


@router.post("/staff/support/{ticket_id}/reopen")
async def staff_reopen_ticket(
    ticket_id: str,
    user: User = Depends(role_required("super_admin", "support")),
) -> dict:
    with SessionLocal() as session:
        ticket = session.get(SupportTicket, uuid.UUID(ticket_id))
        if not ticket:
            return ok({"status": "not_found"})
        ticket.status = "open"
        ticket.updated_at = func.now()
        session.commit()
    return ok({"status": "open"})
