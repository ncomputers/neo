import pathlib
import sys

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))


def test_html_has_report_only_header(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    from api.app.middlewares.security import SecurityMiddleware

    app = FastAPI()
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app.add_middleware(SecurityMiddleware)

    @app.get("/plain")
    def _plain():
        return HTMLResponse("<html></html>")

    client = TestClient(app)
    resp = client.get("/plain")
    header = resp.headers.get("Content-Security-Policy-Report-Only")
    assert header is not None
    assert "report-uri /csp/report" in header
