import os
import pathlib
import sys
import time

import fakeredis.aioredis
import httpx
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DB_URL", "postgresql://localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "http://example.com")
os.environ.setdefault("APP_VERSION", "1")

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from api.app.main import app  # noqa: E402
from api.app.services import printer_watchdog  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    app.state.redis = fakeredis.aioredis.FakeRedis()

    async def fake_check(redis, tenant):
        return False, 0

    monkeypatch.setattr(printer_watchdog, "check", fake_check)

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url):
            return httpx.Response(200)

    monkeypatch.setattr(httpx, "AsyncClient", DummyClient)
    monkeypatch.setattr("socket.gethostbyname", lambda host: "127.0.0.1")
    return TestClient(app)


def test_troubleshoot_all_ok(client):
    now_ms = int(time.time() * 1000)
    resp = client.get(
        f"/admin/troubleshoot?client_epoch={now_ms}",
        headers={"X-App-Version": "1", "X-Tenant-ID": "demo"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["printer"]["ok"] is True
    assert data["time"]["ok"] is True
    assert data["dns"]["ok"] is True
    assert data["version"]["ok"] is True
