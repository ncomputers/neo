from fastapi.testclient import TestClient

from api.app.main import app
from api.app.routes_onboarding import TENANTS


def test_help_page_includes_branding():
    TENANTS["demo"] = {"profile": {"name": "Demo Outlet", "logo_url": "logo.png"}}
    client = TestClient(app)
    resp = client.get("/help/printing?tenant_id=demo")
    assert resp.status_code == 200
    assert "Demo Outlet" in resp.text
    assert "logo.png" in resp.text


def test_help_page_missing_returns_404():
    client = TestClient(app)
    resp = client.get("/help/missing")
    assert resp.status_code == 404
