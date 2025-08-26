import pathlib
import sys
from types import SimpleNamespace

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))  # noqa: E402

import os  # noqa: E402

os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DB_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost")
os.environ.setdefault("SECRET_KEY", "x" * 32)

import fakeredis.aioredis  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.app.main import app  # noqa: E402
from api.app import routes_refunds  # noqa: E402
from api.app.db import SessionLocal  # noqa: E402
from api.app.models_tenant import AuditTenant, Invoice, Payment  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    app.state.redis = fakeredis.aioredis.FakeRedis()

    async def _tenant_id():
        return "demo"

    payment = Payment(id=1, invoice_id=1, mode="gateway", amount=10, verified=True)
    invoice = Invoice(id=1, settled=True, settled_at=None)

    class DummySession:
        def __init__(self):
            self.added = []

        async def get(self, model, pk):
            if model is Payment and pk == 1:
                return payment
            if model is Invoice and pk == 1:
                return invoice
            return None

        def add(self, obj):
            self.added.append(obj)

        async def commit(self):
            pass

    session = DummySession()

    async def _session():
        return session

    app.dependency_overrides[routes_refunds.get_tenant_id] = _tenant_id
    app.dependency_overrides[routes_refunds.get_tenant_session] = _session

    with SessionLocal() as db:
        db.query(AuditTenant).delete()
        db.commit()

    client = TestClient(app, raise_server_exceptions=False)
    yield client, session
    app.dependency_overrides.clear()


def test_duplicate_key_no_double_refund(client):
    client, session = client
    headers = {"Idempotency-Key": "abc"}

    resp1 = client.post("/payments/1/refund", headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["data"]["refunded"] is True

    resp2 = client.post("/payments/1/refund", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json() == resp1.json()
    assert len(session.added) == 1


def test_audit_idempotency_key(client):
    client, _ = client
    key = "key1"
    client.post("/payments/1/refund", headers={"Idempotency-Key": key})

    with SessionLocal() as db:
        row = db.query(AuditTenant).filter_by(action="payment.refund").first()
        assert row is not None
        assert row.meta["idempotency_key"] == key
