import fakeredis.aioredis
import pytest
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from api.app import routes_refunds
from api.app.models_tenant import Invoice, Payment

app = FastAPI()
templates = Jinja2Templates("templates")
app.include_router(routes_refunds.router)


@app.get("/checkout")
async def checkout(request: Request, order_id: int):
    return templates.TemplateResponse(
        "checkout.html",
        {
            "request": request,
            "total": 100,
            "tip_enabled": False,
            "payment_methods": ["cash"],
            "payment_id": 1,
        },
    )


@pytest.fixture
def client():
    app.state.redis = fakeredis.aioredis.FakeRedis()

    payment = Payment(id=1, invoice_id=1, mode="cash", amount=100, verified=True)
    invoice = Invoice(id=1, settled=True, settled_at=None)

    class DummySession:
        async def get(self, model, pk):
            if model is Payment and pk == 1:
                return payment
            if model is Invoice and pk == 1:
                return invoice
            return None

        def add(self, obj):
            pass

        async def commit(self):
            pass

    async def _session():
        return DummySession()

    async def _tenant_id():
        return "demo"

    app.dependency_overrides[routes_refunds.get_tenant_session] = _session
    app.dependency_overrides[routes_refunds.get_tenant_id] = _tenant_id

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_checkout_links_and_refund_confirm(client):
    resp = client.get("/checkout?order_id=1")
    assert resp.status_code == 200
    for path in ("terms", "refund", "contact"):
        assert f"/legal/{path}" in resp.text

    resp = client.post("/payments/1/refund")
    assert resp.status_code == 400

    resp = client.post("/payments/1/refund", headers={"Idempotency-Key": "abc"})
    assert resp.status_code == 200
