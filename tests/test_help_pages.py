from fastapi.testclient import TestClient

from api.app.main import app
from api.app.routes_onboarding import TENANTS


def test_help_renders_docs():
    client = TestClient(app)
    resp = client.get("/help")
    assert resp.status_code == 200
    assert "Owner Onboarding" in resp.text
    assert "Cashier &amp; KDS Cheat Sheet" in resp.text
    assert "Troubleshooting" in resp.text
    assert "Subprocessors" in resp.text
    assert "Service Level Agreement" in resp.text


def test_help_includes_branding():
    TENANTS["demo"] = {"profile": {"name": "Demo Outlet", "logo_url": "logo.png"}}
    client = TestClient(app)
    resp = client.get("/help?tenant_id=demo")
    assert resp.status_code == 200
    assert "Demo Outlet" in resp.text
    assert "logo.png" in resp.text
