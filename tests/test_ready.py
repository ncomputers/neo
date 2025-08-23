import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from api.app.main import app
import api.app.routes_ready as routes_ready


class DummySession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, *args, **kwargs):
        return None


class RedisOK:
    async def ping(self):  # pragma: no cover - simple mock
        return True


class RedisFail:
    async def ping(self):  # pragma: no cover - simple mock
        raise Exception("down")


def test_ready_ok(monkeypatch):
    monkeypatch.setattr(routes_ready, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr("api.app.main.redis_client", RedisOK())
    client = TestClient(app)
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_ready_redis_down(monkeypatch):
    monkeypatch.setattr(routes_ready, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr("api.app.main.redis_client", RedisFail())
    client = TestClient(app)
    resp = client.get("/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "READY_FAIL"
