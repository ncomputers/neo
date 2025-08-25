import pytest
import fakeredis.aioredis
import pathlib
import sys
from datetime import datetime, timezone
import asyncio
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import main as app_main
from api.app.main import app
from api.app.auth import create_access_token

app.state.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)


class _BypassSubGuard:
    async def __call__(self, request, call_next):
        return await call_next(request)


@pytest.fixture(scope="module", autouse=True)
def _setup_teardown():
    original_guard = app_main.subscription_guard
    app_main.subscription_guard = _BypassSubGuard()
    yield
    app_main.subscription_guard = original_guard
    app.dependency_overrides.clear()


def _admin_headers():
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    return {"Authorization": f"Bearer {token}"}


def test_jobs_status_endpoint():
    app.state.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    r = app.state.redis
    now = datetime.now(timezone.utc)

    async def seed() -> None:
        await r.set("jobs:heartbeat:w1", now.isoformat())
        await r.set("jobs:processed:w1", 5)
        await r.zadd(
            "jobs:failures:w1",
            {"a": now.timestamp() - 1800, "b": now.timestamp() - 7200},
        )
        await r.sadd("jobs:queues:w1", "default", "email")
        await r.rpush("jobs:queue:default", "1", "2")
        await r.rpush("jobs:queue:email", "1")

    asyncio.run(seed())

    client = TestClient(app)
    resp = client.get("/api/admin/jobs/status", headers=_admin_headers())

    assert resp.status_code == 200
    data = resp.json()["data"]["w1"]
    assert data["last_heartbeat"] == now.isoformat()
    assert data["processed_count"] == 5
    assert data["failures_1h"] == 1
    assert data["queue_depths"] == {"default": 2, "email": 1}
