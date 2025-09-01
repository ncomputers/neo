import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import fakeredis.aioredis  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from api.app import audit  # noqa: E402
from api.app.audit import Base  # noqa: E402
from api.app.routes_onboarding import router as onboarding_router  # noqa: E402
from api.app.routes_qrpack import router as qrpack_router  # noqa: E402
from api.app.middleware.csp import CSPMiddleware  # noqa: E402


def _setup_app(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path}/audit.db", connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(bind=engine)
    monkeypatch.setattr(audit, "engine", engine)
    monkeypatch.setattr(audit, "SessionLocal", SessionLocal)
    Base.metadata.create_all(bind=engine)

    import api.app.auth as auth  # noqa: E402

    monkeypatch.setattr(auth, "role_required", lambda *roles: lambda: object())
    monkeypatch.setattr(auth, "get_current_user", lambda: object())

    import importlib
    routes_admin_qrpack = importlib.reload(
        __import__("api.app.routes_admin_qrpack", fromlist=["router"])
    )

    app = FastAPI()
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app.add_middleware(CSPMiddleware)
    app.include_router(onboarding_router)
    app.include_router(qrpack_router)
    app.include_router(routes_admin_qrpack.router)
    return app


def test_qrpack_log_and_export(tmp_path, monkeypatch):
    app = _setup_app(tmp_path, monkeypatch)
    client = TestClient(app)

    oid = client.post("/api/onboarding/start").json()["data"]["onboarding_id"]
    client.post(
        f"/api/onboarding/{oid}/profile",
        json={
            "name": "Cafe",
            "address": "1",
            "logo_url": "",
            "timezone": "UTC",
            "language": "en",
        },
    )
    client.post(f"/api/onboarding/{oid}/tables", json={"count": 2})
    client.post(f"/api/onboarding/{oid}/finish")

    resp = client.get(
        f"/api/outlet/{oid}/qrpack.pdf",
        params={
            "pack_id": "P1",
            "count": 2,
            "requester": "alice",
            "reason": "test",
        },
    )
    assert resp.status_code == 200

    resp = client.get("/api/admin/qrpacks/logs", params={"pack_id": "P1"})
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["requester"] == "alice"

    resp = client.get("/api/admin/qrpacks/export", params={"requester": "alice"})
    assert resp.status_code == 200
    assert "P1" in resp.text
    assert resp.headers["content-type"].startswith("text/csv")
