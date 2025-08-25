import importlib.util
import time
import uuid
from datetime import datetime, timedelta, timezone

import fakeredis
import responses
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def _load_worker(monkeypatch):
    monkeypatch.setenv("CB_FAILURE_THRESHOLD", "1")
    monkeypatch.setenv("CB_COOLDOWN_SEC", "1")
    monkeypatch.setenv("CB_HALFOPEN_TRIALS", "1")
    monkeypatch.setenv("WEBHOOK_ALLOW_HOSTS", "example.com")
    spec = importlib.util.spec_from_file_location(
        "notify_worker", "scripts/notify_worker.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.REDIS_CLIENT = fakeredis.FakeRedis()
    return mod


def test_webhook_breaker(monkeypatch):
    notify_worker = _load_worker(monkeypatch)

    engine = create_engine("sqlite:///:memory:")
    notify_worker.NotificationRule.__table__.create(engine)
    notify_worker.NotificationOutbox.__table__.create(engine)
    notify_worker.NotificationDLQ.__table__.create(engine)

    url = "http://example.com/hook"
    url_hash = notify_worker._url_hash(url)

    rule_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            notify_worker.NotificationRule(
                id=rule_id, channel="webhook", config={"url": url}
            )
        )
        session.commit()

    # --- First failure opens breaker ---
    event1 = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            notify_worker.NotificationOutbox(
                id=event1,
                rule_id=rule_id,
                payload={"msg": "hi"},
                status="queued",
            )
        )
        session.commit()

    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, url, status=500)
        notify_worker.process_once(engine)
        assert len(rsps.calls) == 1

    assert (
        notify_worker.webhook_attempts_total.labels(destination=url_hash)._value.get()
        == 1
    )
    assert (
        notify_worker.webhook_failures_total.labels(destination=url_hash)._value.get()
        == 1
    )
    assert (
        notify_worker.webhook_breaker_state.labels(url_hash=url_hash)._value.get() == 1
    )

    # --- Open breaker blocks further attempts ---
    with responses.RequestsMock() as rsps:
        notify_worker.process_once(engine)
        assert len(rsps.calls) == 0

    # --- Half-open trial succeeds and closes breaker ---
    notify_worker.REDIS_CLIENT.set(f"cb:{url_hash}:until", int(time.time()) - 1)
    with Session(engine) as session:
        evt = session.get(notify_worker.NotificationOutbox, event1)
        evt.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.add(evt)
        session.commit()

    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, url, status=200)
        notify_worker.process_once(engine)
        assert len(rsps.calls) == 1

    assert (
        notify_worker.webhook_attempts_total.labels(destination=url_hash)._value.get()
        == 2
    )
    assert (
        notify_worker.webhook_failures_total.labels(destination=url_hash)._value.get()
        == 1
    )
    assert (
        notify_worker.webhook_breaker_state.labels(url_hash=url_hash)._value.get() == 0
    )

    # --- New failure after recovery reopens breaker ---
    event2 = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            notify_worker.NotificationOutbox(
                id=event2,
                rule_id=rule_id,
                payload={"msg": "bye"},
                status="queued",
            )
        )
        session.commit()

    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, url, status=500)
        notify_worker.process_once(engine)
        assert len(rsps.calls) == 1

    assert (
        notify_worker.webhook_attempts_total.labels(destination=url_hash)._value.get()
        == 3
    )
    assert (
        notify_worker.webhook_failures_total.labels(destination=url_hash)._value.get()
        == 2
    )
    assert (
        notify_worker.webhook_breaker_state.labels(url_hash=url_hash)._value.get() == 1
    )

    # --- Half-open failure keeps breaker open and resets cooldown ---
    notify_worker.REDIS_CLIENT.set(f"cb:{url_hash}:until", int(time.time()) - 1)
    with Session(engine) as session:
        evt = session.get(notify_worker.NotificationOutbox, event2)
        evt.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.add(evt)
        session.commit()

    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, url, status=500)
        notify_worker.process_once(engine)
        assert len(rsps.calls) == 1

    assert (
        notify_worker.webhook_attempts_total.labels(destination=url_hash)._value.get()
        == 4
    )
    assert (
        notify_worker.webhook_failures_total.labels(destination=url_hash)._value.get()
        == 3
    )
    assert (
        notify_worker.webhook_breaker_state.labels(url_hash=url_hash)._value.get() == 1
    )
