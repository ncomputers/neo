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
    credit_balance_inr: int = 0


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


@dataclass
class Referral:
    id: str
    referrer_tenant_id: str
    code: str
    landing_url: str
    clicks: int = 0
    signups: int = 0
    converted: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    referred_tenant_id: str | None = None


@dataclass
class ReferralCredit:
    id: str
    tenant_id: str
    amount_inr: int
    reason: str
    applied_invoice_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


PLANS: Dict[str, Plan] = {}
SUBSCRIPTIONS: Dict[str, Subscription] = {}
SUBSCRIPTION_EVENTS: List[SubscriptionEvent] = []
INVOICES: List[BillingInvoice] = []
PROCESSED_EVENTS: set[str] = set()
REFERRALS: Dict[str, Referral] = {}
REFERRAL_CREDITS: List[ReferralCredit] = []


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


def create_referral(referrer_tenant_id: str) -> Referral:
    """Create and return a new referral for ``referrer_tenant_id``."""
    code = uuid.uuid4().hex[:6]
    ref = Referral(
        id=str(uuid.uuid4()),
        referrer_tenant_id=referrer_tenant_id,
        code=code,
        landing_url=f"/signup?ref={code}",
    )
    REFERRALS[code] = ref
    return ref


def record_referral_signup(code: str, referred_tenant_id: str) -> None:
    """Record that ``referred_tenant_id`` signed up via ``code``."""
    ref = REFERRALS.get(code)
    if ref is None:
        return
    if ref.referrer_tenant_id == referred_tenant_id:
        raise ValueError("self-referral")
    ref.signups += 1
    ref.referred_tenant_id = referred_tenant_id


def handle_referral_payment(
    referred_tenant_id: str, invoice_amount: int, plan_price: int
) -> None:
    """Grant credit when the referred tenant pays their first invoice."""
    ref = next(
        (r for r in REFERRALS.values() if r.referred_tenant_id == referred_tenant_id),
        None,
    )
    if ref is None or ref.converted:
        return
    if invoice_amount < plan_price:
        return
    ref.converted += 1
    amount = min(invoice_amount, plan_price)
    credit = ReferralCredit(
        id=str(uuid.uuid4()),
        tenant_id=ref.referrer_tenant_id,
        amount_inr=amount,
        reason="referral",
    )
    REFERRAL_CREDITS.append(credit)
    sub = SUBSCRIPTIONS.get(ref.referrer_tenant_id)
    if sub:
        sub.credit_balance_inr += amount


def apply_credit_to_invoice(tenant_id: str, amount_inr: int) -> int:
    """Apply available credits to ``amount_inr`` and return the net amount."""
    sub = SUBSCRIPTIONS.get(tenant_id)
    if not sub or sub.credit_balance_inr <= 0:
        return amount_inr
    applied = min(sub.credit_balance_inr, amount_inr)
    sub.credit_balance_inr -= applied
    return amount_inr - applied


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
        from ..main import TENANTS  # TENANTS is defined in api.app.main

        now = datetime.utcnow()
        period_end = now + timedelta(days=30)
        sub = SUBSCRIPTIONS.get(tenant_id)
        if sub:
            sub.plan_id = plan.id
            sub.status = "active"
            sub.current_period_start = now
            sub.current_period_end = period_end
        else:
            sub = Subscription(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                plan_id=plan.id,
                status="active",
                current_period_start=now,
                current_period_end=period_end,
            )
            SUBSCRIPTIONS[tenant_id] = sub
        tenant = TENANTS.get(tenant_id)
        if tenant is None:
            tenant = {}
            TENANTS[tenant_id] = tenant
        tenant["plan"] = plan.id
        tenant["subscription_expires_at"] = period_end
        amount = apply_credit_to_invoice(tenant_id, plan.price_inr)
        inv = BillingInvoice(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            number=f"INV-{len(INVOICES)+1:03d}",
            amount_inr=amount,
            gst_inr=int(amount * 0.18),
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
