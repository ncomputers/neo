import logging
import fakeredis.aioredis
import pytest

from api.app import routes_push
from api.app.services import push


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_push_ready_logs(monkeypatch, caplog):
    fake = fakeredis.aioredis.FakeRedis()
    monkeypatch.setattr("api.app.main.redis_client", fake)
    caplog.set_level(logging.INFO, logger="push")

    sub = routes_push.PushSubscription(
        endpoint="https://example.com", keys=routes_push.PushKeys(p256dh="k", auth="a")
    )
    await routes_push.subscribe("demo", "T1", sub)

    await push.notify_ready("demo", "T1", 1)

    assert "web-push queued" in caplog.text
