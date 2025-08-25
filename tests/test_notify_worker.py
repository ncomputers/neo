import importlib.util
import uuid
from datetime import datetime, timedelta, timezone
import hashlib

import pytest
import responses
import fakeredis
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

# Dynamically import the worker module
spec = importlib.util.spec_from_file_location(
    "notify_worker", "scripts/notify_worker.py"
)
notify_worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notify_worker)


@pytest.fixture(autouse=True)
def fake_redis():
    notify_worker.REDIS_CLIENT = fakeredis.FakeRedis()
    yield
    notify_worker.REDIS_CLIENT.flushall()


def test_console_delivery():
    engine = create_engine("sqlite:///:memory:")
    notify_worker.NotificationRule.__table__.create(engine)
    notify_worker.NotificationOutbox.__table__.create(engine)
    notify_worker.NotificationDLQ.__table__.create(engine)

    rule_id = uuid.uuid4()
    event_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            notify_worker.NotificationRule(id=rule_id, channel="console", config={})
        )
        session.add(
            notify_worker.NotificationOutbox(
                id=event_id,
                rule_id=rule_id,
                payload={"msg": "hi"},
                status="queued",
            )
        )
        session.commit()

    notify_worker.process_once(engine)

    with Session(engine) as session:
        evt = session.get(notify_worker.NotificationOutbox, event_id)
        assert evt is not None
        assert evt.status == "delivered"


def test_whatsapp_delivery():
    engine = create_engine("sqlite:///:memory:")
    notify_worker.NotificationRule.__table__.create(engine)
    notify_worker.NotificationOutbox.__table__.create(engine)
    notify_worker.NotificationDLQ.__table__.create(engine)

    rule_id = uuid.uuid4()
    event_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            notify_worker.NotificationRule(
                id=rule_id, channel="whatsapp", config={"target": "123"}
            )
        )
        session.add(
            notify_worker.NotificationOutbox(
                id=event_id,
                rule_id=rule_id,
                payload={"msg": "hi"},
                status="queued",
            )
        )
        session.commit()

    notify_worker.process_once(engine)

    with Session(engine) as session:
        evt = session.get(notify_worker.NotificationOutbox, event_id)
        assert evt is not None
        assert evt.status == "delivered"


def test_sms_delivery():
    engine = create_engine("sqlite:///:memory:")
    notify_worker.NotificationRule.__table__.create(engine)
    notify_worker.NotificationOutbox.__table__.create(engine)
    notify_worker.NotificationDLQ.__table__.create(engine)

    rule_id = uuid.uuid4()
    event_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            notify_worker.NotificationRule(
                id=rule_id, channel="sms", config={"target": "123"}
            )
        )
        session.add(
            notify_worker.NotificationOutbox(
                id=event_id,
                rule_id=rule_id,
                payload={"msg": "hi"},
                status="queued",
            )
        )
        session.commit()

    notify_worker.process_once(engine)

    with Session(engine) as session:
        evt = session.get(notify_worker.NotificationOutbox, event_id)
        assert evt is not None
        assert evt.status == "delivered"


def test_slack_delivery(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    notify_worker.NotificationRule.__table__.create(engine)
    notify_worker.NotificationOutbox.__table__.create(engine)
    notify_worker.NotificationDLQ.__table__.create(engine)

    rule_id = uuid.uuid4()
    event_id = uuid.uuid4()
    url = "http://slack.local/webhook"
    monkeypatch.setenv("SLACK_WEBHOOK_URL", url)

    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, url, json={}, status=200)
        with Session(engine) as session:
            session.add(
                notify_worker.NotificationRule(id=rule_id, channel="slack", config={})
            )
            session.add(
                notify_worker.NotificationOutbox(
                    id=event_id,
                    rule_id=rule_id,
                    payload={"text": "hi"},
                    status="queued",
                )
            )
            session.commit()

        notify_worker.process_once(engine)
        assert len(rsps.calls) == 1

    with Session(engine) as session:
        evt = session.get(notify_worker.NotificationOutbox, event_id)
        assert evt is not None
        assert evt.status == "delivered"


def test_webhook_failures_move_to_dlq(monkeypatch):
    monkeypatch.setenv("OUTBOX_MAX_ATTEMPTS", "2")
    engine = create_engine("sqlite:///:memory:")
    notify_worker.NotificationRule.__table__.create(engine)
    notify_worker.NotificationOutbox.__table__.create(engine)
    notify_worker.NotificationDLQ.__table__.create(engine)

    rule_id = uuid.uuid4()
    event_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            notify_worker.NotificationRule(id=rule_id, channel="webhook", config={})
        )
        session.add(
            notify_worker.NotificationOutbox(
                id=event_id,
                rule_id=rule_id,
                payload={"msg": "hi"},
                status="queued",
            )
        )
        session.commit()

    notify_worker.process_once(engine)
    with Session(engine) as session:
        evt = session.get(notify_worker.NotificationOutbox, event_id)
        assert evt is not None
        assert evt.attempts == 1
        assert evt.next_attempt_at is not None
        assert evt.next_attempt_at > datetime.utcnow()

    # Second run should be skipped because next_attempt_at is in the future
    notify_worker.process_once(engine)
    with Session(engine) as session:
        evt = session.get(notify_worker.NotificationOutbox, event_id)
        assert evt is not None
        assert evt.attempts == 1
        evt.next_attempt_at = datetime.utcnow() - timedelta(seconds=1)
        session.add(evt)
        session.commit()

    notify_worker.process_once(engine)
    with Session(engine) as session:
        evt = session.get(notify_worker.NotificationOutbox, event_id)
        assert evt is not None
        assert evt.attempts == 2
        evt.next_attempt_at = datetime.utcnow() - timedelta(seconds=1)
        session.add(evt)
        session.commit()

    notify_worker.process_once(engine)
    with Session(engine) as session:
        evt = session.get(notify_worker.NotificationOutbox, event_id)
        assert evt is None
        dlq = session.scalars(select(notify_worker.NotificationDLQ)).one()
        assert dlq.original_id == event_id


def test_webhook_circuit_breaker(monkeypatch):
    monkeypatch.setenv("WEBHOOK_BREAKER_THRESHOLD", "1")
    monkeypatch.setenv("WEBHOOK_BREAKER_OPEN_SECS", "1")
    monkeypatch.setenv("WEBHOOK_ALLOW_HOSTS", "example.com")
    notify_worker.BREAKER_THRESHOLD = 1
    notify_worker.BREAKER_OPEN_SECS = 1
    engine = create_engine("sqlite:///:memory:")
    notify_worker.NotificationRule.__table__.create(engine)
    notify_worker.NotificationOutbox.__table__.create(engine)
    notify_worker.NotificationDLQ.__table__.create(engine)

    rule_id = uuid.uuid4()
    event_id = uuid.uuid4()
    url = "http://example.com/hook"
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
    with Session(engine) as session:
        session.add(
            notify_worker.NotificationRule(
                id=rule_id, channel="webhook", config={"url": url}
            )
        )
        session.add(
            notify_worker.NotificationOutbox(
                id=event_id,
                rule_id=rule_id,
                payload={"msg": "hi"},
                status="queued",
            )
        )
        session.commit()

    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, url, status=500)
        # first attempt fails and opens breaker
        notify_worker.process_once(engine)
        assert len(rsps.calls) == 1
    assert (
        notify_worker.webhook_attempts_total.labels(destination=url)._value.get() == 1
    )
    assert (
        notify_worker.webhook_failures_total.labels(destination=url)._value.get() == 1
    )
    assert notify_worker.webhook_breaker_state.labels(url_hash=url_hash)._value.get() == 1

    # breaker should prevent immediate retry
    with responses.RequestsMock() as rsps:
        notify_worker.process_once(engine)
        assert len(rsps.calls) == 0

    # expire breaker and allow half-open trial
    notify_worker.REDIS_CLIENT.delete(f"wh:breaker:{url_hash}")
    with Session(engine) as session:
        evt = session.get(notify_worker.NotificationOutbox, event_id)
        evt.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.add(evt)
        session.commit()

    delivered_states: list[int] = []
    original = notify_worker._deliver

    def capture(rule, event):
        delivered_states.append(
            notify_worker.webhook_breaker_state.labels(url_hash=url_hash)._value.get()
        )
        return original(rule, event)

    monkeypatch.setattr(notify_worker, "_deliver", capture)

    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, url, status=200)
        notify_worker.process_once(engine)
        assert len(rsps.calls) == 1
    assert delivered_states[-1] == 2
    assert (
        notify_worker.webhook_attempts_total.labels(destination=url)._value.get() == 2
    )
    assert (
        notify_worker.webhook_failures_total.labels(destination=url)._value.get() == 1
    )
    assert notify_worker.webhook_breaker_state.labels(url_hash=url_hash)._value.get() == 0

    with Session(engine) as session:
        evt = session.get(notify_worker.NotificationOutbox, event_id)
        assert evt is not None
        assert evt.status == "delivered"
