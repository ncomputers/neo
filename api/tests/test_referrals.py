import importlib
import pathlib
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient
import fakeredis.aioredis

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.routes_onboarding import TENANTS
import api.app.routes_referrals as referrals


def _setup_app() -> FastAPI:
    app = FastAPI()
    app.include_router(referrals.router)
    app.state.redis = fakeredis.aioredis.FakeRedis()
    return app


def test_referral_signup_self_and_ratelimit(monkeypatch):
    monkeypatch.setenv("RL_REFERRAL_SIGNUP_BURST", "1")
    monkeypatch.setenv("RL_REFERRAL_SIGNUP_RPM", "1")
    importlib.reload(referrals)

    TENANTS.clear()
    TENANTS["t1"] = {"owner": {"email": "a@example.com", "phone": "123"}}

    app = _setup_app()
    client = TestClient(app)

    # self-referral by email
    resp = client.post(
        "/referrals/signup",
        json={"referrer_tenant_id": "t1", "email": "a@example.com", "phone": "999"},
    )
    assert resp.status_code == 400

    # fresh app for rate limit test
    app = _setup_app()
    client = TestClient(app)
    payload = {"referrer_tenant_id": "t1", "email": "b@example.com", "phone": "999"}
    assert client.post("/referrals/signup", json=payload).status_code == 200
    assert client.post("/referrals/signup", json=payload).status_code == 429


def test_referral_credit_cap_invoice_idempotent(monkeypatch):
    monkeypatch.setenv("REFERRAL_MAX_CREDITS", "100")
    importlib.reload(referrals)
    referrals.REFERRAL_CREDITS.clear()
    referrals.SUBSCRIPTION_EVENTS.clear()

    app = _setup_app()
    client = TestClient(app)

    payload = {
        "event_id": "e1",
        "referrer_tenant_id": "t1",
        "amount_inr": 60,
        "invoice_amount_inr": 100,
        "plan_price_inr": 50,
    }
    assert client.post("/referrals/credit", json=payload).json()["data"]["awarded"] == 60

    payload2 = {
        "event_id": "e2",
        "referrer_tenant_id": "t1",
        "amount_inr": 60,
        "invoice_amount_inr": 100,
        "plan_price_inr": 50,
    }
    assert client.post("/referrals/credit", json=payload2).json()["data"]["awarded"] == 40

    payload3 = {
        "event_id": "e3",
        "referrer_tenant_id": "t1",
        "amount_inr": 10,
        "invoice_amount_inr": 40,
        "plan_price_inr": 50,
    }
    assert client.post("/referrals/credit", json=payload3).json()["data"]["awarded"] == 0

    # replay event should be idempotent
    assert client.post("/referrals/credit", json=payload2).json()["data"]["awarded"] == 0
