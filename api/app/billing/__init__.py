from __future__ import annotations

"""In-memory billing domain models and gateway."""

import hashlib
import hmac
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Protocol


@dataclass
class Plan:
    id: str
    name: str
    price_inr: int
    billing_interval: str
    max_tables: int
    features_json: Dict[str, Any]
    is_active: bool = True


@dataclass
class Subscription:
    id: str
    tenant_id: str
    plan_id: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    trial_end: datetime | None = None
    cancel_at_period_end: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SubscriptionEvent:
    id: str
    subscription_id: str
    type: str
    payload_json: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BillingInvoice:
    id: str
    tenant_id: str
    number: str
    amount_inr: int
    gst_inr: int
    period_start: datetime
    period_end: datetime
    status: str
    pdf_url: str
    created_at: datetime = field(default_factory=datetime.utcnow)


PLANS: Dict[str, Plan] = {}
SUBSCRIPTIONS: Dict[str, Subscription] = {}
SUBSCRIPTION_EVENTS: List[SubscriptionEvent] = []
INVOICES: List[BillingInvoice] = []
PROCESSED_EVENTS: set[str] = set()


def seed_default_plans() -> None:
    if PLANS:
        return
    PLANS["starter"] = Plan(
        id="starter",
        name="Starter",
        price_inr=0,
        billing_interval="monthly",
        max_tables=5,
        features_json={},
    )
    PLANS["standard"] = Plan(
        id="standard",
        name="Standard",
        price_inr=4999,
        billing_interval="monthly",
        max_tables=20,
        features_json={"exports": True},
    )
    PLANS["pro"] = Plan(
        id="pro",
        name="Pro",
        price_inr=9999,
        billing_interval="monthly",
        max_tables=50,
        features_json={"exports": True, "coupons": True},
    )


seed_default_plans()


class BillingGateway(Protocol):
    def create_checkout_session(self, tenant_id: str, plan: Plan) -> Dict[str, Any]:
        """Create a checkout session for ``tenant_id`` and ``plan``."""

    def verify_webhook(self, sig: str, body: bytes) -> bool:
        """Validate webhook signature."""

    def list_payments(self, tenant_id: str) -> List[Dict[str, Any]]:
        """List payments for ``tenant_id``."""


class MockGateway:
    """Mock gateway that auto-succeeds payments."""

    secret = "mock_secret"

    def create_checkout_session(self, tenant_id: str, plan: Plan) -> Dict[str, Any]:
        from .main import TENANTS  # inline import to avoid circular deps

        now = datetime.utcnow()
        period_end = now + timedelta(days=30)
        sub = Subscription(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            plan_id=plan.id,
            status="active",
            current_period_start=now,
            current_period_end=period_end,
        )
        SUBSCRIPTIONS[tenant_id] = sub
        TENANTS[tenant_id]["plan"] = plan.id
        TENANTS[tenant_id]["subscription_expires_at"] = period_end
        inv = BillingInvoice(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            number=f"INV-{len(INVOICES)+1:03d}",
            amount_inr=plan.price_inr,
            gst_inr=int(plan.price_inr * 0.18),
            period_start=now,
            period_end=period_end,
            status="paid",
            pdf_url="/invoices/mock.pdf",
        )
        INVOICES.append(inv)
        SUBSCRIPTION_EVENTS.append(
            SubscriptionEvent(
                id=str(uuid.uuid4()),
                subscription_id=sub.id,
                type="payment_succeeded",
                payload_json={"plan": plan.id},
            )
        )
        return {"checkout_session_id": str(uuid.uuid4())}

    def verify_webhook(self, sig: str, body: bytes) -> bool:
        expected = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)

    def list_payments(
        self, tenant_id: str
    ) -> List[Dict[str, Any]]:  # pragma: no cover - stub
        return []
