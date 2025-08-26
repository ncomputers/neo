from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.app.middlewares.prometheus import PrometheusMiddleware
from api.app.slo import slo_tracker


def test_slo_metrics_and_admin_endpoint(monkeypatch):
    # bypass auth for admin route
    import importlib

    import api.app.auth as auth

    monkeypatch.setattr(auth, "role_required", lambda *roles: (lambda: object()))
    import api.app.routes_admin_ops as admin_ops

    importlib.reload(admin_ops)

    # reset tracker
    slo_tracker.requests.clear()
    slo_tracker.errors.clear()

    app = FastAPI()
    app.add_middleware(PrometheusMiddleware)
    app.include_router(admin_ops.router)

    @app.get("/ok")
    def ok_route():
        return {"ok": True}

    @app.get("/boom")
    def boom_route():  # pragma: no cover - simple test handler
        raise HTTPException(status_code=500, detail="boom")

    client = TestClient(app)

    client.get("/ok")
    client.get("/boom")

    resp = client.get("/admin/ops/slo")
    data = resp.json()["data"]

    assert data["/ok"]["requests"] == 1
    assert data["/ok"]["errors"] == 0
    assert data["/boom"]["requests"] == 1
    assert data["/boom"]["errors"] == 1
