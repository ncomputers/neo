import importlib.util
import fakeredis.aioredis
import pytest

from api.app import routes_push
from api.app.services import push
from api.app.db import SessionLocal, engine
from api.app.models_master import (
    Base as MasterBase,
    NotificationOutbox,
    NotificationRule,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_push_ready_enqueues_outbox(monkeypatch):
    fake = fakeredis.aioredis.FakeRedis()
    monkeypatch.setattr("api.app.main.redis_client", fake)

    sub = routes_push.PushSubscription(
        endpoint="https://example.com",
        keys=routes_push.PushKeys(p256dh="k", auth="a"),
    )
    await routes_push.subscribe("demo", "T1", sub)

    MasterBase.metadata.drop_all(bind=engine)
    MasterBase.metadata.create_all(bind=engine)

    await push.notify_ready("demo", "T1", 1)

    spec = importlib.util.spec_from_file_location(
        "notify_worker", "scripts/notify_worker.py"
    )
    notify_worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(notify_worker)

    with SessionLocal() as session:
        events = session.query(NotificationOutbox).all()
        assert len(events) == 1
        event = events[0]
        rule = session.get(NotificationRule, event.rule_id)
        assert rule.channel == "webpush"

    notify_worker.process_once(engine)

    with SessionLocal() as session:
        evt = session.get(NotificationOutbox, event.id)
        assert evt.status == "delivered"
