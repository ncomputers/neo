import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.auth import create_access_token, UserInDB, fake_users_db
from api.app.routes_feedback import router, FEEDBACK_STORE
import scripts.nps_digest as nps_digest

app = FastAPI()
app.include_router(router)

client = TestClient(app)


def setup_module():
    fake_users_db["guest@example.com"] = UserInDB(
        username="guest@example.com", role="guest", password_hash=""
    )
    app.state.redis = fakeredis.aioredis.FakeRedis()
    FEEDBACK_STORE.clear()


def test_submit_and_summary():
    guest = create_access_token({"sub": "guest@example.com", "role": "guest"})
    admin = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    headers_guest = {"Authorization": f"Bearer {guest}"}
    headers_admin = {"Authorization": f"Bearer {admin}"}

    assert (
        client.post(
            "/api/outlet/demo/feedback",
            json={"score": 9, "comment": "great"},
            headers=headers_guest,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/outlet/demo/feedback",
            json={"score": 4, "comment": "slow"},
            headers=headers_guest,
        ).status_code
        == 200
    )

    resp = client.get("/api/outlet/demo/feedback/summary", headers=headers_admin)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data == {
        "nps": 0.0,
        "promoters": 1,
        "detractors": 1,
        "responses": 2,
    }

    from datetime import datetime

    summary = nps_digest.aggregate(datetime.utcnow().date())
    assert summary["demo"] == 0.0
