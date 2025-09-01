import importlib
import pathlib
import sys

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))


def test_guest_page_headers(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://allowed.com")
    monkeypatch.setenv("ENABLE_HSTS", "1")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)

    import api.app.config.cors as cors
    import api.app.middleware.cors as cors_mw
    import api.app.middlewares.csp as csp
    import api.app.middlewares.security as security

    importlib.reload(cors)
    importlib.reload(cors_mw)
    importlib.reload(csp)
    importlib.reload(security)
    CORSMiddleware = cors_mw.CORSMiddleware
    CSPMiddleware = csp.CSPMiddleware
    SecurityMiddleware = security.SecurityMiddleware

    app = FastAPI()
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app.add_middleware(
        CORSMiddleware, allowed_origins=["https://allowed.com"]
    )
    app.add_middleware(CSPMiddleware)
    app.add_middleware(SecurityMiddleware)

    @app.get("/g/test")
    def _guest():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/g/test", headers={"Origin": "https://allowed.com"})
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert (
        resp.headers.get("Referrer-Policy")
        == "strict-origin-when-cross-origin"
    )
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("access-control-allow-origin") == "https://allowed.com"
    assert (
        resp.headers.get("Strict-Transport-Security")
        == "max-age=31536000; includeSubDomains; preload"
    )
