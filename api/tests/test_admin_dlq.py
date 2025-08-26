import asyncio
import json
import pathlib
import sys

import fakeredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app import audit  # noqa: E402
from api.app.auth import create_access_token  # noqa: E402
from api.app.routes_dlq import router as dlq_router  # noqa: E402

app = FastAPI()
app.include_router(dlq_router)
app.state.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture(scope="module", autouse=True)
def _setup_teardown():
    audit.Base.metadata.drop_all(bind=audit.engine)
    audit.Base.metadata.create_all(bind=audit.engine)
    yield
    app.dependency_overrides.clear()


def _admin_headers():
    token = create_access_token({"sub": "admin@example.com", "role": "super_admin"})
    return {"Authorization": f"Bearer {token}"}


def test_dlq_list_and_replay():
    r = app.state.redis

    async def seed() -> None:
        await r.rpush(
            "jobs:dlq:webhook",
            json.dumps(
                {
                    "id": "1",
                    "type": "webhook",
                    "created_at": 123,
                    "reason": "boom",
                    "last_error": "trace",
                }
            ),
        )

    asyncio.run(seed())

    client = TestClient(app)
    resp = client.get(
        "/api/admin/dlq",
        params={"type": "webhook"},
        headers=_admin_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == "1"
    assert data[0]["reason"] == "boom"

    resp = client.post(
        "/api/admin/dlq/replay",
        params={"type": "webhook"},
        headers=_admin_headers(),
        json={"id": "1"},
    )
    assert resp.status_code == 200

    async def check() -> tuple[int, list[str]]:
        dlq_len = await r.llen("jobs:dlq:webhook")
        queued = await r.lrange("jobs:queue:webhook", 0, -1)
        return dlq_len, queued

    dlq_len, queued = asyncio.run(check())
    assert dlq_len == 0
    assert queued == [
        json.dumps(
            {
                "id": "1",
                "type": "webhook",
                "created_at": 123,
                "reason": "boom",
                "last_error": "trace",
            }
        )
    ]
