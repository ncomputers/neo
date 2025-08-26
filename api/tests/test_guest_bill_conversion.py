import os
import pathlib
import sys
import types

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")
os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)

sys.modules.setdefault("api.app.routes_admin_pilot", types.SimpleNamespace(router=None))
sys.modules.setdefault("api.app.routes_admin_print", types.SimpleNamespace(router=None))

from fastapi.testclient import TestClient
import fakeredis.aioredis

from api.app.main import app
from api.app.routes_guest_bill import get_tenant_id, get_tenant_session
from api.app.repos_sqlalchemy import invoices_repo_sql
from api.app.services import notifications, billing_service
from api.app.routes_metrics import ab_conversions_total


async def _fake_generate_invoice(*args, **kwargs):
    return 1


async def _fake_get_tenant_session():
    class _Dummy:
        pass
    return _Dummy()


def _setup_app(monkeypatch):
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app.dependency_overrides[get_tenant_id] = lambda: "demo"
    app.dependency_overrides[get_tenant_session] = _fake_get_tenant_session
    async def _fake_enqueue(*a, **k):
        return None
    monkeypatch.setattr(invoices_repo_sql, "generate_invoice", _fake_generate_invoice)
    monkeypatch.setattr(billing_service, "compute_bill", lambda *a, **k: {})
    monkeypatch.setattr(notifications, "enqueue", _fake_enqueue)
    return TestClient(app)


def test_records_conversion(monkeypatch):
    client = _setup_app(monkeypatch)
    before = ab_conversions_total.labels(
        experiment="MENU_COPY_V1", variant="treat"
    )._value.get()
    # Force variant
    monkeypatch.setattr(
        "api.app.routes_guest_bill.get_variant", lambda *a, **k: "treat"
    )
    resp = client.post("/g/T-001/bill", headers={"device-id": "abc"}, json={})
    assert resp.status_code == 200
    after = ab_conversions_total.labels(
        experiment="MENU_COPY_V1", variant="treat"
    )._value.get()
    assert after == before + 1
    app.dependency_overrides.clear()
