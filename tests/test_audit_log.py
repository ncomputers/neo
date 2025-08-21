import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.app.db as app_db
import api.app.utils as app_utils
sys.modules.setdefault("db", app_db)
sys.modules.setdefault("utils", app_utils)

from api.app.superadmin_stub import router as super_router
from api.app.db import SessionLocal
from api.app.models_tenant import AuditTenant


class DummyRedis:
    async def sismember(self, *args, **kwargs):
        return False

    async def incr(self, *args, **kwargs):
        return 0

    async def sadd(self, *args, **kwargs):
        return 0


def test_audit_log_inserts_row(monkeypatch):
    monkeypatch.setenv("POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///test_{tenant_id}.db")
    app = FastAPI()
    app.state.redis = DummyRedis()
    app.include_router(super_router)
    client = TestClient(app)

    resp = client.post("/api/super/outlet/check", json={"name": "Cafe"})
    assert resp.status_code == 200

    with SessionLocal() as session:
        row = session.query(AuditTenant).filter_by(action="outlet_check").first()
        assert row is not None
        assert row.actor == "guest"
        assert row.meta["path"] == "/api/super/outlet/check"
        assert row.meta["payload"]["name"] == "Cafe"
