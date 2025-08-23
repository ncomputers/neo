import importlib.util
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

# Dynamically import the worker module
spec = importlib.util.spec_from_file_location(
    "notify_worker", "scripts/notify_worker.py"
)
notify_worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notify_worker)


def _raise(*args, **kwargs):
    raise requests.RequestException("boom")


def test_console_delivery():
    engine = create_engine("sqlite:///:memory:")
    notify_worker.NotificationOutbox.__table__.create(engine)
    notify_worker.NotificationDLQ.__table__.create(engine)

    with Session(engine) as session:
        session.add(
            notify_worker.NotificationOutbox(
                event="ping",
                payload={"msg": "hi"},
                channel="console",
                target="-",
                status="queued",
            )
        )
        session.commit()

    notify_worker.process_once(engine)

    with Session(engine) as session:
        evt = session.execute(select(notify_worker.NotificationOutbox)).scalar_one()
        assert evt.status == "delivered"


def test_webhook_retry_and_dlq(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    notify_worker.NotificationOutbox.__table__.create(engine)
    notify_worker.NotificationDLQ.__table__.create(engine)
    notify_worker.MAX_ATTEMPTS = 2

    with Session(engine) as session:
        session.add(
            notify_worker.NotificationOutbox(
                event="ping",
                payload={"msg": "hi"},
                channel="webhook",
                target="https://example.com/hook",
                status="queued",
            )
        )
        session.commit()

    monkeypatch.setattr(notify_worker.requests, "post", _raise)

    # first attempt -> retry scheduled
    notify_worker.process_once(engine)
    with Session(engine) as session:
        evt = session.execute(select(notify_worker.NotificationOutbox)).scalar_one()
        assert evt.attempts == 1
        assert evt.next_attempt_at is not None
        evt.next_attempt_at = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
        session.add(evt)
        session.commit()

    # second attempt -> move to DLQ
    notify_worker.process_once(engine)
    with Session(engine) as session:
        outbox_rows = session.execute(select(notify_worker.NotificationOutbox)).all()
        dlq_rows = session.execute(select(notify_worker.NotificationDLQ)).all()
        assert outbox_rows == []
        assert len(dlq_rows) == 1
        assert dlq_rows[0][0].original_id is not None
