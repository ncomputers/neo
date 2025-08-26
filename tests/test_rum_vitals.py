from __future__ import annotations

from fastapi.testclient import TestClient

from api.app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_route_whitelist_accept_and_reject():
    client = _client()
    # accepted and normalized
    ok_resp = client.post(
        "/rum/vitals",
        headers={"X-Tenant-ID": "tenant"},
        json={"route": "/admin/foo?x=1", "consent": True},
    )
    assert ok_resp.status_code == 200

    # rejected unknown route
    bad_resp = client.post(
        "/rum/vitals",
        headers={"X-Tenant-ID": "tenant"},
        json={"route": "/evil", "consent": True},
    )
    assert bad_resp.status_code == 422

    # rejected long route
    long_route = "/" + "a" * 65
    long_resp = client.post(
        "/rum/vitals",
        headers={"X-Tenant-ID": "tenant"},
        json={"route": long_route, "consent": True},
    )
    assert long_resp.status_code == 422


def test_invalid_vital_values_return_422():
    client = _client()
    resp = client.post(
        "/rum/vitals",
        headers={"X-Tenant-ID": "tenant"},
        json={"route": "/admin", "lcp": -1, "consent": True},
    )
    assert resp.status_code == 422

    resp2 = client.post(
        "/rum/vitals",
        headers={"X-Tenant-ID": "tenant"},
        json={"route": "/admin", "cls": 3, "consent": True},
    )
    assert resp2.status_code == 422
