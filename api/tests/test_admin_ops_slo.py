import os
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app import routes_slo


def test_admin_slo_endpoint(monkeypatch):
    app = FastAPI()
    app.state.redis = fakeredis.aioredis.FakeRedis()

    class FakeResponse:
        def json(self):
            return {
                "status": "success",
                "data": {
                    "result": [{"metric": {"route": "/g/test"}, "value": [0, "0.1"]}]
                },
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def get(self, url, params=None):
            return FakeResponse()

    class FakeHttpx:
        AsyncClient = FakeClient
        HTTPError = Exception

    monkeypatch.setattr(routes_slo, "httpx", FakeHttpx)

    app.include_router(routes_slo.router)
    client = TestClient(app)
    resp = client.get("/admin/ops/slo")
    assert resp.status_code == 200
    assert resp.json() == {"/g/test": {"error_rate": 0.1, "error_budget": 0.9}}
