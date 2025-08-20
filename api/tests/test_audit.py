# test_audit.py

"""Ensure audit logs record and purge events correctly."""

import pathlib
import sys
from datetime import datetime, timedelta

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
import fakeredis.aioredis

from api.app import audit
from api.app.main import app

client = TestClient(app)


def setup_module() -> None:
    """Reset audit tables and configure a fake Redis instance."""

    app.state.redis = fakeredis.aioredis.FakeRedis()
    audit.Base.metadata.drop_all(bind=audit.engine)
    audit.Base.metadata.create_all(bind=audit.engine)


def test_audit_logging_and_cleanup() -> None:
    """Events should be logged and old rows purged based on retention."""

    client.post(
        "/login/email", json={"username": "admin@example.com", "password": "adminpass"}
    )
    client.post(
        "/tables/t1/cart", json={"item": "tea", "price": 2.0, "quantity": 1}
    )
    client.post("/tables/t1/order")
    client.patch("/tables/t1/order/0", json={"quantity": 0, "admin": True})
    client.post("/tables/t1/pay")

    with audit.SessionLocal() as session:
        assert session.query(audit.AuditMaster).count() == 1
        assert session.query(audit.Audit).count() == 2
        old = audit.Audit(
            actor="old",
            action="old",
            entity="x",
            created_at=datetime.utcnow() - timedelta(days=40),
        )
        session.add(old)
        session.commit()

    audit.purge_old_logs(days=30)

    with audit.SessionLocal() as session:
        assert session.query(audit.Audit).filter_by(actor="old").count() == 0

