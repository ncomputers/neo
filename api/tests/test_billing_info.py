from datetime import datetime, timedelta

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

from api.app.main import TENANTS, app


@pytest.fixture
def client():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    TENANTS.clear()


def test_billing_endpoint_shows_grace(client, monkeypatch):
    monkeypatch.setenv("LICENSE_PAY_URL", "upi://pay")
    resp = client.post("/tenants", params={"name": "t1", "licensed_tables": 1})
    tenant_id = resp.json()["data"]["tenant_id"]
    TENANTS[tenant_id]["plan"] = "basic"
    TENANTS[tenant_id]["subscription_expires_at"] = datetime.utcnow() - timedelta(days=1)
    headers = {"X-Tenant-ID": tenant_id}
    resp_bill = client.get("/billing", headers=headers)
    assert resp_bill.status_code == 200
    data = resp_bill.json()["data"]
    assert data["plan"] == "basic"
    assert data["pay_url"]
    assert data["grace"] is True

