import importlib
import pathlib
import sys
import time

import fakeredis.aioredis
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))


def _setup_app(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://allowed.com")
    monkeypatch.setenv("RATE_LIMIT_LOGIN", "2/1s")
    monkeypatch.setenv("RATE_LIMIT_REFRESH", "60/5m")
    monkeypatch.setenv("DB_URL", "postgresql://localhost/test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    from api.app import main as app_main

    importlib.reload(app_main)
    app_main.app.state.redis = fakeredis.aioredis.FakeRedis()
    return app_main.app


def test_csp_header_blocks_inline(monkeypatch):
    app = _setup_app(monkeypatch)
    client = TestClient(app)
    resp = client.get("/health", headers={"Origin": "https://allowed.com"})
    csp = resp.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "script-src 'self' 'nonce-" in csp
    for part in csp.split(";"):
        if part.strip().startswith("script-src"):
            assert "'unsafe-inline'" not in part
            break
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert (
        resp.headers.get("Permissions-Policy")
        == "geolocation=(), microphone=(), camera=(), notifications=(self)"
    )


def test_cors_rejects_unknown_origin(monkeypatch):
    app = _setup_app(monkeypatch)
    client = TestClient(app)
    resp = client.get("/ready", headers={"Origin": "https://evil.com"})
    assert resp.status_code == 403


def test_login_rate_limit_resets(monkeypatch):
    app = _setup_app(monkeypatch)
    client = TestClient(app)
    for _ in range(2):
        resp = client.post(
            "/login/pin",
            json={"username": "cashier1", "pin": "bad"},
        )
        assert resp.status_code == 400
    resp = client.post(
        "/login/pin",
        json={"username": "cashier1", "pin": "bad"},
    )
    assert resp.status_code == 429
    assert resp.headers.get("Retry-After")
    time.sleep(1)
    resp = client.post(
        "/login/pin",
        json={"username": "cashier1", "pin": "bad"},
    )
    assert resp.status_code == 400


def test_sw_not_served_on_admin(monkeypatch):
    app = _setup_app(monkeypatch)
    client = TestClient(app)
    resp = client.get('/admin/')
    assert 'Service-Worker' not in resp.headers
    assert 'Service-Worker-Allowed' not in resp.headers
