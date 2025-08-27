from __future__ import annotations

import importlib
import os

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_app() -> FastAPI:
    import api.app.routes_onboarding as ro

    app = FastAPI()
    app.include_router(ro.router)
    return app


def test_onboarding_progress_persist(tmp_path):
    db_path = tmp_path / "onboarding.db"
    os.environ["ONBOARDING_DB"] = str(db_path)
    import api.app.onboarding_store as store

    importlib.reload(store)
    import api.app.routes_onboarding as ro

    importlib.reload(ro)

    app = _build_app()
    client = TestClient(app)
    start = client.post("/api/onboarding/start").json()["data"]
    oid = start["onboarding_id"]
    profile = {
        "name": "Cafe Neo",
        "address": "1 Example St",
        "timezone": "UTC",
        "language": "en",
    }
    assert (
        client.post(f"/api/onboarding/{oid}/profile", json=profile).status_code == 200
    )

    # simulate restart by reloading modules and new app
    importlib.reload(store)
    importlib.reload(ro)
    app2 = _build_app()
    client2 = TestClient(app2)
    state = client2.get(f"/api/onboarding/{oid}").json()["data"]
    assert state["current_step"] == "profile"
    assert state["profile"]["name"] == "Cafe Neo"

    assert (
        client2.post(f"/api/onboarding/{oid}/tables", json={"count": 2}).status_code
        == 200
    )
    state2 = client2.get(f"/api/onboarding/{oid}").json()["data"]
    assert state2["current_step"] == "tables"
    assert len(state2["tables"]) == 2
