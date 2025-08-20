# test_ratelimit.py
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
import fakeredis.aioredis

from api.app.main import app


def test_ip_block_after_three_failures():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    client = TestClient(app)
    for _ in range(3):
        resp = client.post(
            "/login/email",
            json={"username": "admin@example.com", "password": "wrong"},
        )
        assert resp.status_code == 400
    resp = client.post(
        "/login/email",
        json={"username": "admin@example.com", "password": "wrong"},
    )
    assert resp.status_code == 403
