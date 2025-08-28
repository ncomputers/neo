from __future__ import annotations

"""Owner billing endpoints using a mock gateway."""

import csv
import io
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy import text

from .billing import (
    PLANS,
    PROCESSED_EVENTS,
    SUBSCRIPTION_EVENTS,
    MockGateway,
    SubscriptionEvent,
)
from .billing.invoice_service import create_invoice
from .db import SessionLocal
from .middlewares.license_gate import billing_always_allowed
from .utils.responses import ok

router = APIRouter(prefix="/admin/billing")
webhook_router = APIRouter()
_gateway = MockGateway()


@router.get("/subscription")
@billing_always_allowed
async def get_subscription(x_tenant_id: str = Header(...)) -> dict:
    from .main import TENANTS  # inline import to avoid circular deps

    tenant = TENANTS.get(x_tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    plan_id = tenant.get("plan")
    expiry = tenant.get("subscription_expires_at")
    grace_days = tenant.get("grace_period_days", 7)
    now = datetime.utcnow()
    grace = False
    days_left = None
    status = "inactive"
    if expiry:
        days_left = (expiry - now).days
        if now <= expiry:
            status = "active"
        elif now <= expiry + timedelta(days=grace_days):
            status = "grace"
            grace = True
        else:
            status = "expired"
    return ok(
        {
            "plan": plan_id,
            "status": status,
            "days_left": days_left,
            "grace": grace,
        }
    )


@router.post("/checkout")
@billing_always_allowed
async def checkout(payload: dict, x_tenant_id: str = Header(...)) -> dict:
    plan_id = payload.get("plan_id")
    plan = PLANS.get(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    session = _gateway.create_checkout_session(x_tenant_id, plan)
    return ok(session)


@router.get("/invoice/{invoice_id}.pdf")
@billing_always_allowed
async def invoice_pdf(invoice_id: int):
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT pdf_path FROM billing_invoices WHERE id=:id"),
            {"id": invoice_id},
        ).fetchone()
    if not row or not row[0] or not Path(row[0]).exists():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(row[0], media_type="application/pdf")


@router.get("/credit-note/{credit_note_id}.pdf")
@billing_always_allowed
async def credit_note_pdf(credit_note_id: int):
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT pdf_path FROM billing_credit_notes WHERE id=:id"),
            {"id": credit_note_id},
        ).fetchone()
    if not row or not row[0] or not Path(row[0]).exists():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(row[0], media_type="application/pdf")


@router.post("/invoice/test-generate")
@billing_always_allowed
async def test_generate(payload: dict) -> dict:
    invoice_id = create_invoice(
        payload["tenant_id"],
        payload["plan_id"],
        datetime.fromisoformat(payload["period_start"]),
        datetime.fromisoformat(payload["period_end"]),
        Decimal(str(payload["amount_inr"])),
        payload.get("buyer_gstin"),
    )
    return ok({"invoice_id": invoice_id})


@router.get("/invoices.csv")
@billing_always_allowed
async def invoices_csv(
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None, alias="to"),
) -> Response:
    with SessionLocal() as db:
        query = "SELECT id, number, amount_inr, cgst_inr, sgst_inr, igst_inr FROM billing_invoices"
        params = {}
        if from_ and to:
            query += " WHERE created_at BETWEEN :f AND :t"
            params = {"f": from_, "t": to}
        rows = db.execute(text(query), params).fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "number", "amount_inr", "cgst_inr", "sgst_inr", "igst_inr"])
    for r in rows:
        writer.writerow([r[0], r[1], r[2], r[3], r[4], r[5]])
    return Response(buf.getvalue(), media_type="text/csv")


@router.post("/dunning/snooze")
@billing_always_allowed
async def dunning_snooze(response: Response) -> dict:
    """Set a cookie to suppress renewal banners for the day."""
    from datetime import timezone

    expires = datetime.now(timezone.utc).replace(
        hour=23, minute=59, second=59, microsecond=0
    )
    response.set_cookie("dunning_snooze", "1", expires=expires)
    return ok({"snoozed_until": expires.isoformat()})


@webhook_router.post("/billing/webhook/mock")
@billing_always_allowed
async def mock_webhook(request: Request, x_mock_signature: str = Header(...)) -> dict:
    body = await request.body()
    if not _gateway.verify_webhook(x_mock_signature, body):
        raise HTTPException(status_code=401, detail="invalid signature")
    payload = json.loads(body)
    event_id = payload.get("id")
    if event_id in PROCESSED_EVENTS:
        return ok({"id": event_id})
    PROCESSED_EVENTS.add(event_id)
    SUBSCRIPTION_EVENTS.append(
        SubscriptionEvent(
            id=event_id,
            subscription_id=payload.get("subscription_id", ""),
            type=payload.get("type", ""),
            payload_json=payload,
        )
    )
    return ok({"id": event_id})
