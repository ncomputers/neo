import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
import fakeredis.aioredis

from api.app.routes_onboarding import router as onboarding_router, TENANTS
from api.app.routes_qrpack import router as qrpack_router



def _setup_app() -> FastAPI:
    """Return app with onboarding and QR pack routers for testing."""
    app = FastAPI()
    app.include_router(onboarding_router)
    app.include_router(qrpack_router)
    app.state.redis = fakeredis.aioredis.FakeRedis()
    return app


def test_onboarding_end_to_end_flow_and_qrpack_render():
    app = _setup_app()
    client = TestClient(app)

    start = client.post("/api/onboarding/start").json()["data"]
    oid = start["onboarding_id"]

    profile = {
        "name": "Cafe Neo",
        "address": "1, Example St",
        "logo_url": "http://logo/neo.png",
        "timezone": "UTC",
        "language": "en",
    }
    assert (
        client.post(f"/api/onboarding/{oid}/profile", json=profile).status_code
        == 200
    )

    tax = {"mode": "regular", "gstin": "GST123", "hsn_required": True}
    assert client.post(f"/api/onboarding/{oid}/tax", json=tax).status_code == 200

    table_resp = (
        client.post(f"/api/onboarding/{oid}/tables", json={"count": 6}).json()["data"]
    )
    assert len(table_resp) == 6

    payments = {
        "vpa": "neo@upi",
        "central_vpa": True,
        "modes": {"cash": True, "upi": True, "card": False},
    }
    assert (
        client.post(f"/api/onboarding/{oid}/payments", json=payments).status_code
        == 200
    )

    finish = client.post(f"/api/onboarding/{oid}/finish").json()["data"]
    tid = finish["tenant_id"]

    tenant = TENANTS[tid]
    assert tenant["tax"]["mode"] == "regular"
    assert len(tenant["tables"]) == 6

    for t in tenant["tables"]:
        link = f"https://example.com/{tid}/{t['qr_token']}"
        assert link.startswith(f"https://example.com/{tid}/")
        assert len(t["qr_token"]) == 32

    resp = client.get(f"/api/outlet/{tid}/qrpack.pdf", params={"per_page": 12})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf") or resp.headers[
        "content-type"
    ].startswith("text/html")
