import asyncio
from contextlib import asynccontextmanager

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_guest_receipts_flow(monkeypatch):
    from api.app import routes_guest_bill, routes_guest_receipts
    from api.app.services import billing_service

    async def _gen_invoice(**k):
        return 1

    monkeypatch.setattr(
        routes_guest_bill.invoices_repo_sql, "generate_invoice", _gen_invoice
    )
    monkeypatch.setattr(
        billing_service,
        "compute_bill",
        lambda *a, **k: {
            "subtotal": 100,
            "tax_breakup": {5: 5},
            "total": 105,
        },
    )

    app = FastAPI()
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app.include_router(routes_guest_bill.router)
    app.include_router(routes_guest_receipts.router)

    @asynccontextmanager
    async def _session_override():
        yield None

    app.dependency_overrides[routes_guest_bill.get_tenant_id] = lambda: "t1"
    app.dependency_overrides[routes_guest_bill.get_tenant_session] = _session_override

    client = TestClient(app)

    for _ in range(12):
        resp = client.post(
            "/g/x/bill",
            json={"phone": "123", "consent": True},
        )
        assert resp.status_code == 200

    resp = client.get("/guest/receipts", params={"phone": "123"})
    data = resp.json()["data"]["receipts"]
    assert len(data) == 10
    assert "tax_breakup" not in data[0]

    ttl = asyncio.get_event_loop().run_until_complete(
        app.state.redis.ttl("receipts:123")
    )
    assert ttl >= 30 * 86400 - 1
