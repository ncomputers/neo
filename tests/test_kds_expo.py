import asyncio
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.routes_kds_expo import router
from api.app.utils.responses import ok
from api.app.models_tenant import AuditTenant
from api.app.db import SessionLocal


class DummyResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class Row:
    def __init__(self, ready_at):
        self.id = 1
        self.code = "T1"
        self.ready_at = ready_at
        self.allergens = ["nuts"]


class DummySession:
    async def execute(self, *_args, **_kwargs):
        ready_at = datetime.now(timezone.utc) - timedelta(seconds=30)
        return DummyResult([Row(ready_at)])

from contextlib import asynccontextmanager


@asynccontextmanager
async def dummy_session(_tenant_id):
    yield DummySession()


async def fake_transition(tenant_id, order_id, dest):
    return ok({"status": dest.value})


def test_ready_to_picked(monkeypatch):
    monkeypatch.setattr("api.app.routes_kds_expo._session", dummy_session)
    monkeypatch.setattr("api.app.routes_kds_expo._transition_order", fake_transition)

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    with SessionLocal() as s:
        s.query(AuditTenant).delete()
        s.commit()

    resp = client.get("/kds/expo", headers={"X-Tenant-ID": "t1"})
    assert resp.status_code == 200
    tickets = resp.json()["data"]["tickets"]
    assert tickets[0]["order_id"] == 1
    assert tickets[0]["allergen_badges"] == ["nuts"]

    resp = client.post("/kds/expo/1/picked", headers={"X-Tenant-ID": "t1"})
    assert resp.status_code == 200

    with SessionLocal() as s:
        row = s.query(AuditTenant).filter_by(action="expo.picked").first()
        assert row is not None
        assert row.meta["path"] == "/kds/expo/1/picked"
