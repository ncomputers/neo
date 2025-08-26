import asyncio
import json
import pathlib
import sys

import fakeredis

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import main as app_main
from api.app.main import app
from api.app.auth import create_access_token


app.state.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
from api.app import main as app_main  # noqa: E402
from api.app.audit import AuditMaster  # noqa: E402
from api.app.audit import SessionLocal as AuditSession  # noqa: E402
from api.app.auth import create_access_token  # noqa: E402
from api.app.main import app  # noqa: E402



class _BypassSubGuard:
    async def __call__(self, request, call_next):
        return await call_next(request)


@pytest.fixture(scope="module", autouse=True)
def _setup_teardown():

    app.state.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    # reset audit tables
    from api.app import audit

    audit.Base.metadata.drop_all(bind=audit.engine)
    audit.Base.metadata.create_all(bind=audit.engine)

    original_guard = app_main.subscription_guard
    app_main.subscription_guard = _BypassSubGuard()
    yield
    app_main.subscription_guard = original_guard
    app.dependency_overrides.clear()


def _admin_headers():
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    return {"Authorization": f"Bearer {token}"}


def test_dlq_list_and_replay():
    r = app.state.redis

    async def seed() -> None:
        await r.rpush(
            "jobs:dlq:webhook",
            json.dumps({"id": "1", "payload": {"foo": "bar"}}),

        )

    asyncio.run(seed())

    client = TestClient(app)
    resp = client.get("/api/admin/dlq", params={"type": "webhook"}, headers=_admin_headers())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == "1"

    resp = client.post(
        "/api/admin/dlq/replay/1",
        params={"type": "webhook"},

        headers=_admin_headers(),
    )
    assert resp.status_code == 200

    async def check() -> tuple[int, list[str]]:
        dlq_len = await r.llen("jobs:dlq:webhook")
        queued = await r.lrange("jobs:queue:webhook", 0, -1)
        return dlq_len, queued

    dlq_len, queued = asyncio.run(check())
    assert dlq_len == 0
    assert queued == [json.dumps({"id": "1", "payload": {"foo": "bar"}})]
