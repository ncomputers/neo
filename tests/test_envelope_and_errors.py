import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from api.app.main import app


class DummyRedis:
    async def sismember(self, *args, **kwargs):
        return False

    async def incr(self, *args, **kwargs):
        return 0

    async def sadd(self, *args, **kwargs):
        return 0


app.state.redis = DummyRedis()


def test_health_ok():
    client = TestClient(app)
    resp = client.get("/health", headers={"X-Request-ID": "abc"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "data": {"status": "ok"}}
    assert resp.headers["X-Request-ID"] == "abc"


def test_not_found_returns_err():
    client = TestClient(app)
    resp = client.get("/missing")
    assert resp.status_code == 404
    body = resp.json()
    assert body["ok"] is False
    assert body["error"]["code"] == 404
