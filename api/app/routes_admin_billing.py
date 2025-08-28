from __future__ import annotations

"""Owner billing endpoints using a mock gateway."""

import csv
import io
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Header, HTTPException, Request, Response

from .billing import (
    INVOICES,
    PLANS,
    PROCESSED_EVENTS,
    SUBSCRIPTION_EVENTS,
    MockGateway,
    SubscriptionEvent,
)
from .utils.responses import ok

router = APIRouter(prefix="/admin/billing")
webhook_router = APIRouter()
_gateway = MockGateway()


@router.get("/subscription")
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
async def checkout(payload: dict, x_tenant_id: str = Header(...)) -> dict:
    plan_id = payload.get("plan_id")
    plan = PLANS.get(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    session = _gateway.create_checkout_session(x_tenant_id, plan)
    return ok(session)


@router.get("/invoices.csv")
async def invoices_csv(x_tenant_id: str = Header(...)) -> Response:
    rows = [inv for inv in INVOICES if inv.tenant_id == x_tenant_id]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "number",
            "amount_inr",
            "gst_inr",
            "period_start",
            "period_end",
            "status",
            "pdf_url",
        ]
    )
    for inv in rows:
        writer.writerow(
            [
                inv.number,
                inv.amount_inr,
                inv.gst_inr,
                inv.period_start.isoformat(),
                inv.period_end.isoformat(),
                inv.status,
                inv.pdf_url,
            ]
        )
    return Response(buf.getvalue(), media_type="text/csv")


@webhook_router.post("/billing/webhook/mock")
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
