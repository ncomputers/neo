import importlib.util
import uuid
from datetime import datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

# Dynamically import the worker module
spec = importlib.util.spec_from_file_location(
    "notify_worker", "scripts/notify_worker.py"
)
notify_worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notify_worker)


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
