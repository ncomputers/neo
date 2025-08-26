import os
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DB_URL", "postgresql://localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost/0")
os.environ.setdefault("SECRET_KEY", "x" * 32)

from fastapi import HTTPException
from fastapi.testclient import TestClient
import fakeredis.aioredis

from api.app.main import app


def test_slo_counters():
    app.state.redis = fakeredis.aioredis.FakeRedis()

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
