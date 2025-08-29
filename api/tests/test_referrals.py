import os
import sys
import types
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[2]))

# Stub optional dependencies
sys.modules.setdefault("opentelemetry", types.ModuleType("opentelemetry"))
sys.modules.setdefault("opentelemetry.trace", types.ModuleType("trace"))
sys.modules.setdefault("qrcode", types.ModuleType("qrcode"))

os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("POSTGRES_MASTER_URL", "postgresql://localhost")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from api.app import billing
from api.app.billing import (
    apply_credit_to_invoice,
    create_referral,
    handle_referral_payment,
    record_referral_signup,
)
from api.app.main import TENANTS, app


@pytest.fixture
def client():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    TENANTS.clear()
    billing.SUBSCRIPTIONS.clear()
    billing.SUBSCRIPTION_EVENTS.clear()
    billing.INVOICES.clear()
    billing.PROCESSED_EVENTS.clear()
    billing.REFERRALS.clear()
    billing.REFERRAL_CREDITS.clear()


def _make_tenant(client, name: str) -> str:
    resp = client.post("/tenants", params={"name": name, "licensed_tables": 1})
    return resp.json()["data"]["tenant_id"]


def test_referral_credit_flow(client):
    referrer = _make_tenant(client, "A")
    referred = _make_tenant(client, "B")
    now = datetime.utcnow()
    billing.SUBSCRIPTIONS[referrer] = billing.Subscription(
        id=str(uuid.uuid4()),
        tenant_id=referrer,
        plan_id="standard",
        status="active",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    ref = create_referral(referrer)
    record_referral_signup(ref.code, referred)
    handle_referral_payment(referred, invoice_amount=4999, plan_price=4999)
    assert billing.SUBSCRIPTIONS[referrer].credit_balance_inr == 4999
    net = apply_credit_to_invoice(referrer, 3000)
    assert net == 0
    assert billing.SUBSCRIPTIONS[referrer].credit_balance_inr == 1999
    resp = client.get("/admin/billing/credits", headers={"X-Tenant-ID": referrer})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["balance"] == 1999
    assert data["referrals"] == 4999
    assert data["adjustments"] == 0


def test_self_referral_blocked():
    billing.REFERRALS.clear()
    ref = create_referral("t1")
    with pytest.raises(ValueError):
        record_referral_signup(ref.code, "t1")
