import importlib
import pathlib
import sys

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))


def test_allowed_origins_env(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://allowed.com")
    monkeypatch.setenv("DB_URL", "postgresql://localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    from api.app import main as app_main

    importlib.reload(app_main)
    app_main.app.state.redis = fakeredis.aioredis.FakeRedis()

    client = TestClient(app_main.app)
    resp_ok = client.get("/ready", headers={"Origin": "https://allowed.com"})
    assert resp_ok.headers.get("access-control-allow-origin") == "https://allowed.com"

    resp_block = client.get("/ready", headers={"Origin": "https://allowed.com.evil"})
    assert resp_block.status_code == 403

    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    with pytest.raises(RuntimeError):
        importlib.reload(app_main)


def test_security_headers(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://allowed.com")
    monkeypatch.setenv("ENABLE_HSTS", "1")
    monkeypatch.setenv("DB_URL", "postgresql://localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    from api.app import main as app_main

    importlib.reload(app_main)
    app_main.app.state.redis = fakeredis.aioredis.FakeRedis()

    from fastapi import Response

    @app_main.app.get("/cookie")
    def _cookie(response: Response):
        response.set_cookie("a", "b")
        return {"ok": True}

    client = TestClient(app_main.app)
    resp = client.get("/health", headers={"Origin": "https://allowed.com"})
    assert resp.headers.get("access-control-allow-origin") == "https://allowed.com"
    assert resp.headers.get("Referrer-Policy") == "same-origin"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert (
        resp.headers.get("Strict-Transport-Security")
        == "max-age=31536000; includeSubDomains"
    )
    csp = resp.headers.get("Content-Security-Policy")
    assert csp and "default-src 'self'" in csp and "img-src 'self'" in csp
    cookie_resp = client.get("/cookie")
    cookie = cookie_resp.headers.get("set-cookie")
    assert cookie is not None
    lower_cookie = cookie.lower()
    assert "httponly" in lower_cookie
    assert "secure" in lower_cookie
    assert "samesite=lax" in lower_cookie

    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("ENABLE_HSTS", raising=False)
    with pytest.raises(RuntimeError):
        importlib.reload(app_main)
