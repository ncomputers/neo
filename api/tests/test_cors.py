import importlib
import pathlib
import sys

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))


def test_allowed_origins_env(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://allowed.com")
    from api.app import main as app_main

    importlib.reload(app_main)
    app_main.app.state.redis = fakeredis.aioredis.FakeRedis()

    client = TestClient(app_main.app)
    resp_ok = client.get("/ready", headers={"Origin": "https://allowed.com"})
    assert resp_ok.headers.get("access-control-allow-origin") == "https://allowed.com"

    resp_block = client.get("/ready", headers={"Origin": "https://bad.com"})
    assert resp_block.status_code == 403

    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    with pytest.raises(RuntimeError):
        importlib.reload(app_main)


def test_security_headers(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://allowed.com")
    monkeypatch.setenv("ENABLE_HSTS", "1")
    from api.app import main as app_main

    importlib.reload(app_main)
    app_main.app.state.redis = fakeredis.aioredis.FakeRedis()

    client = TestClient(app_main.app)
    resp = client.get("/ready", headers={"Origin": "https://allowed.com"})
    assert resp.headers.get("Referrer-Policy") == "no-referrer"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert (
        resp.headers.get("Content-Security-Policy")
        == "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'"
    )
    assert (
        resp.headers.get("Strict-Transport-Security")
        == "max-age=31536000; includeSubDomains"
    )

    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("ENABLE_HSTS", raising=False)
    with pytest.raises(RuntimeError):
        importlib.reload(app_main)
