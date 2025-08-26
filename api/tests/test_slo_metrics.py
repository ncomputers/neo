import os
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)

import fakeredis.aioredis
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.app.middlewares.prometheus import PrometheusMiddleware
from api.app.routes_metrics import router as metrics_router


def test_slo_counters():
    app = FastAPI()
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app.add_middleware(PrometheusMiddleware)
    app.include_router(metrics_router)

    @app.get("/g/test_ok")
    async def test_ok():
        return {"ok": True}

    @app.get("/g/test_fail")
    async def test_fail():
        raise HTTPException(status_code=500, detail="boom")

    client = TestClient(app)
    client.get("/g/test_ok")
    client.get("/g/test_fail")
    body = client.get("/metrics").text
    assert 'slo_requests_total{route="/g/test_ok"} 1.0' in body
    assert 'slo_requests_total{route="/g/test_fail"} 1.0' in body
    assert 'slo_errors_total{route="/g/test_fail"} 1.0' in body
