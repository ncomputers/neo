import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.auth import create_access_token, UserInDB, fake_users_db
from api.app.routes_feedback import router, FEEDBACK_STORE

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
            json={"table_code": "T1", "rating": "up"},
            headers=headers_guest,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/outlet/demo/feedback",
            json={"table_code": "T1", "rating": "down", "note": "slow"},
            headers=headers_guest,
        ).status_code
        == 200
    )

    resp = client.get("/api/outlet/demo/feedback/summary", headers=headers_admin)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data == {"up": 1, "down": 1}
