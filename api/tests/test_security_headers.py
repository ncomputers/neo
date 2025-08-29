import importlib
import pathlib
import sys

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))


def _setup_app(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://allowed.com")
    monkeypatch.setenv("DB_URL", "postgresql://localhost/test")
    monkeypatch.setenv("POSTGRES_MASTER_URL", "postgresql://localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    from api.app import main as app_main
    importlib.reload(app_main)
    app_main.app.state.redis = fakeredis.aioredis.FakeRedis()
    return app_main.app


def test_csp_header(monkeypatch):
    app = _setup_app(monkeypatch)
    client = TestClient(app)
    resp = client.get("/health", headers={"Origin": "https://allowed.com"})
    csp = resp.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "script-src 'self' 'nonce-" in csp


def test_cors_blocks_unknown_origin(monkeypatch):
    app = _setup_app(monkeypatch)
    client = TestClient(app)
    resp = client.get("/ready", headers={"Origin": "https://evil.com"})
    assert resp.status_code == 403


def test_login_rate_limit(monkeypatch):
    app = _setup_app(monkeypatch)
    client = TestClient(app)
    for _ in range(3):
        resp = client.post(
            "/login/email",
            json={"username": "admin@example.com", "password": "wrong"},
        )
        assert resp.status_code == 400
    resp = client.post(
        "/login/email",
        json={"username": "admin@example.com", "password": "wrong"},
    )
    assert resp.status_code == 403
