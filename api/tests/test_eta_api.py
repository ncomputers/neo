from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.eta import service as eta_service
from api.app.routes_eta import router as eta_router

app = FastAPI()
app.include_router(eta_router)
client = TestClient(app)


def test_get_eta(monkeypatch):
    now = datetime.utcnow()
    fake = {"eta_ms": 1000, "promised_at": now, "components": []}

    monkeypatch.setattr(eta_service, "eta_for_order", lambda *a, **k: fake)
    resp = client.get("/orders/1/eta")
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["eta_ms"] == 1000
    assert "promised_at" in body
