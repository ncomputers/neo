from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.app import routes_slo
from api.app.middlewares.prometheus import PrometheusMiddleware
from api.app.routes_metrics import router as metrics_router


def test_slo_metrics_and_admin_endpoint(monkeypatch):
    app = FastAPI()
    app.add_middleware(PrometheusMiddleware)
    app.include_router(routes_slo.router)
    app.include_router(metrics_router)

    @app.get("/ok")
    def ok_route():
        return {"ok": True}

    @app.get("/boom")
    def boom_route():  # pragma: no cover - simple test handler
        raise HTTPException(status_code=500, detail="boom")

    class FakeResponse:
        def json(self):
            return {
                "status": "success",
                "data": {
                    "result": [
                        {"metric": {"route": "/ok"}, "value": [0, "0"]},
                        {"metric": {"route": "/boom"}, "value": [0, "1"]},
                    ]
                },
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def get(self, url, params=None):
            return FakeResponse()

    class FakeHttpx:
        AsyncClient = FakeClient
        HTTPError = Exception

    monkeypatch.setattr(routes_slo, "httpx", FakeHttpx)

    client = TestClient(app)

    client.get("/ok")
    client.get("/boom")

    body = client.get("/metrics").text
    assert 'slo_requests_total{route="/ok"} 1.0' in body
    assert 'slo_errors_total{route="/boom"} 1.0' in body
    resp = client.get("/admin/ops/slo")
    assert resp.json()["/boom"]["error_rate"] == 1.0
