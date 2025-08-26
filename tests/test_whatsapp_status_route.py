from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app import routes_whatsapp_status
from api.app.db import SessionLocal
from api.app.models_tenant import AuditTenant


def _cleanup():
    with SessionLocal() as session:
        session.query(AuditTenant).delete()
        session.commit()


def test_whatsapp_route_sends_and_audits(monkeypatch):
    _cleanup()
    monkeypatch.setenv("FLAG_WA_ENABLED", "1")
    calls = {}

    def fake_send(event, payload, target):
        calls.setdefault("count", 0)
        calls["count"] += 1
        return "msg123"

    monkeypatch.setattr(routes_whatsapp_status.whatsapp_stub, "send", fake_send)
    app = FastAPI()
    app.include_router(routes_whatsapp_status.router)
    client = TestClient(app)

    resp = client.post(
        "/api/outlet/t1/whatsapp/status",
        json={"phone": "+1", "order_id": 1, "status": "accepted"},
    )
    assert resp.status_code == 200
    assert calls["count"] == 1
    with SessionLocal() as session:
        audit = session.query(AuditTenant).first()
        assert audit is not None
        assert audit.meta["msg_id"] == "msg123"
    _cleanup()


def test_whatsapp_route_retries_on_5xx(monkeypatch):
    _cleanup()
    monkeypatch.setenv("FLAG_WA_ENABLED", "1")
    calls = {"count": 0}

    class Boom(Exception):
        status_code = 500

    def fake_send(event, payload, target):
        calls["count"] += 1
        if calls["count"] < 3:
            raise Boom()
        return "okid"

    monkeypatch.setattr(routes_whatsapp_status.whatsapp_stub, "send", fake_send)

    async def _no_sleep(*a, **k):
        return None

    monkeypatch.setattr(routes_whatsapp_status.asyncio, "sleep", _no_sleep)
    app = FastAPI()
    app.include_router(routes_whatsapp_status.router)
    client = TestClient(app)

    resp = client.post(
        "/api/outlet/t1/whatsapp/status",
        json={"phone": "+1", "order_id": 1, "status": "ready"},
    )
    assert resp.status_code == 200
    assert calls["count"] == 3
    with SessionLocal() as session:
        audit = session.query(AuditTenant).first()
        assert audit is not None
        assert audit.meta["msg_id"] == "okid"
    _cleanup()
