import pathlib
import sys

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.routes_csp import router as csp_router
from api.app.staff_auth import create_staff_token


def _admin_headers():
    token = create_staff_token(1, "super_admin")
    return {"Authorization": f"Bearer {token}"}


def _client(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    app = FastAPI()
    app.state.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app.include_router(csp_router)
    return TestClient(app)


def test_csp_report_storage(monkeypatch):
    client = _client(monkeypatch)
    for i in range(501):
        client.post("/csp/report", json={"n": i})

    resp = client.get("/admin/csp/reports", headers=_admin_headers())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 500
    assert data[0]["n"] == 1


def test_csp_report_redaction(monkeypatch):
    client = _client(monkeypatch)
    report = {
        "csp-report": {
            "document-uri": "https://x.test/?token=abc&x=1",
            "blocked-uri": "https://bad/?token=def",
        }
    }
    client.post("/csp/report", json=report)

    resp = client.get("/admin/csp/reports", headers=_admin_headers())
    assert resp.status_code == 200
    data = resp.json()["data"]
    redacted = data[0]["csp-report"]
    assert redacted["document-uri"] == "https://x.test/?token=***&x=1"
    assert redacted["blocked-uri"] == "https://bad/?token=***"
