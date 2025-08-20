import importlib.util
import uuid

import requests
import responses
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

# Dynamically import the worker module
spec = importlib.util.spec_from_file_location(
    "sync_worker", "ops/scripts/sync_worker.py"
)
sync_worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_worker)


def test_worker_offline_then_online():
    engine = create_engine("sqlite:///:memory:")
    sync_worker.SyncOutbox.__table__.create(engine)
    event_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            sync_worker.SyncOutbox(
                id=event_id, event_type="ping", payload={"hello": "world"}
            )
        )
        session.commit()

    # First attempt fails due to connectivity issues
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            "http://cloud/api",
            body=requests.ConnectionError("offline"),
        )
        sync_worker.process_once(engine, "http://cloud/api")

    with Session(engine) as session:
        event = session.get(sync_worker.SyncOutbox, event_id)
        assert event is not None
        assert event.retries == 1

    # Second attempt succeeds when connectivity returns
    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, "http://cloud/api", json={}, status=200)
        sync_worker.process_once(engine, "http://cloud/api")

    with Session(engine) as session:
        remaining = session.scalars(select(sync_worker.SyncOutbox)).all()
        assert remaining == []
