import io
import zipfile

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.routes_onboarding import router as onboarding_router
from api.app.routes_admin_qrposter_pack import router as poster_router


def _setup_app():
    app = FastAPI()
    app.include_router(onboarding_router)
    app.include_router(poster_router)
    return app


def _onboard(client: TestClient, count: int) -> str:
    oid = client.post("/api/onboarding/start").json()["data"]["onboarding_id"]
    client.post(
        f"/api/onboarding/{oid}/profile",
        json={
            "name": "Cafe",
            "address": "1 St",
            "logo_url": "",
            "timezone": "UTC",
            "language": "en",
        },
    )
    client.post(f"/api/onboarding/{oid}/tables", json={"count": count})
    client.post(f"/api/onboarding/{oid}/finish")
    return oid


def test_poster_pack_contains_pdfs():
    app = _setup_app()
    client = TestClient(app)

    oid = _onboard(client, 2)
    resp = client.get(f"/api/admin/outlets/{oid}/qrposters.zip")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/zip")

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = zf.namelist()
    assert len(names) == 2
    sample = zf.read(names[0])
    assert b"Table 1" in sample
    assert b"Scan to order" in sample
