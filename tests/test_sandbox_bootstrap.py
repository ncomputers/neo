from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.auth import create_access_token
from api.app.routes_sandbox_bootstrap import (
    _SANDBOX_TENANTS,
    _purge_expired,
    router as sandbox_router,
)


app = FastAPI()
app.include_router(sandbox_router)


def _admin_headers():
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    return {"Authorization": f"Bearer {token}"}


def test_sandbox_creation_and_no_pii():
    client = TestClient(app)
    resp = client.post("/admin/tenant/sandbox", headers=_admin_headers())
    assert resp.status_code == 200
    sandbox_id = resp.json()["data"]["tenant_id"]
    assert sandbox_id in _SANDBOX_TENANTS

    sandbox = _SANDBOX_TENANTS[sandbox_id]

    def contains_pii(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in {"email", "phone", "customer"}:
                    return True
                if contains_pii(v):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if contains_pii(item):
                    return True
        return False

    assert not contains_pii(sandbox)


def test_sandbox_expiration():
    client = TestClient(app)
    resp = client.post("/admin/tenant/sandbox", headers=_admin_headers())
    sandbox_id = resp.json()["data"]["tenant_id"]
    # simulate expiry
    _SANDBOX_TENANTS[sandbox_id]["expires_at"] = datetime.utcnow() - timedelta(seconds=1)
    _purge_expired(datetime.utcnow())
    assert sandbox_id not in _SANDBOX_TENANTS
