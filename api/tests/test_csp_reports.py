import importlib
import pathlib
import sys

import fakeredis.aioredis
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.staff_auth import create_staff_token


def _admin_headers():
    token = create_staff_token(1, "super_admin")
    return {"Authorization": f"Bearer {token}"}


def test_csp_report_storage(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")
    monkeypatch.setenv("DB_URL", "postgresql://localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    from api.app import main as app_main

    importlib.reload(app_main)
    app_main.app.state.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    client = TestClient(app_main.app)

    for i in range(501):
        client.post("/csp/report", json={"n": i})

    resp = client.get("/admin/csp/reports", headers=_admin_headers())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 500
    assert data[0]["n"] == 1
