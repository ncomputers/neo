"""Audit coverage for L1 support console routes."""

import pathlib
import sys
from fastapi import FastAPI
from fastapi.testclient import TestClient
import fakeredis.aioredis

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.routes_admin_support_console import router
from api.app.db import SessionLocal
from api.app.models_tenant import AuditTenant
from api.app.auth import create_access_token

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _token() -> str:
    return create_access_token({"sub": "admin@example.com", "role": "super_admin"})


def test_support_console_audit() -> None:
    app.state.redis = fakeredis.aioredis.FakeRedis()
    with SessionLocal() as session:
        session.query(AuditTenant).delete()
        session.commit()

    token = _token()
    resp = client.get(
        "/admin/support/console/search",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    paths = [
        "/admin/support/console/order/1/resend_invoice",
        "/admin/support/console/order/1/reprint_kot",
        "/admin/support/console/order/1/replay_webhook",
        "/admin/support/console/staff/1/unlock_pin",
    ]
    for p in paths:
        resp = client.post(p, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    with SessionLocal() as session:
        actions = {r.action for r in session.query(AuditTenant).all()}
    assert actions == {
        "support.console.search",
        "support.console.resend_invoice",
        "support.console.reprint_kot",
        "support.console.replay_webhook",
        "support.console.unlock_pin",
    }
