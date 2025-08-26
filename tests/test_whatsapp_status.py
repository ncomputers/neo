import asyncio

from api.app.db import SessionLocal
from api.app.models_master import NotificationOutbox, NotificationRule
from api.app.models_tenant import AuditTenant
from api.app.services import whatsapp


def _cleanup():
    with SessionLocal() as session:
        session.query(NotificationOutbox).delete()
        session.query(NotificationRule).delete()
        session.query(AuditTenant).delete()
        session.commit()


def test_notify_status_enqueues_and_audits():
    _cleanup()
    asyncio.run(whatsapp.notify_status("t1", "+123", 42, "accepted"))
    with SessionLocal() as session:
        outbox = session.query(NotificationOutbox).all()
        rule = session.query(NotificationRule).first()
        audit = session.query(AuditTenant).first()
    assert len(outbox) == 1
    assert rule.config["target"] == "+123"
    assert audit.meta["msg_id"] == str(outbox[0].id)
    _cleanup()


def test_notify_status_skips_without_phone():
    _cleanup()
    asyncio.run(whatsapp.notify_status("t1", None, 1, "accepted"))
    with SessionLocal() as session:
        assert session.query(NotificationOutbox).count() == 0
        assert session.query(AuditTenant).count() == 0
    _cleanup()
