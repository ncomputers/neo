from __future__ import annotations

"""WhatsApp notification helpers."""

import logging
from typing import Optional

from ..db import SessionLocal
from ..models_master import NotificationOutbox, NotificationRule
from ..models_tenant import AuditTenant

logger = logging.getLogger("whatsapp")


async def notify_status(tenant: str, phone: Optional[str], order_id: int, status: str) -> None:
    """Queue a WhatsApp message for an order status update.

    If ``phone`` is ``None`` the notification is skipped. A corresponding audit
    entry is recorded with the queued message identifier.
    """

    if not phone:
        return

    payload = {"order_no": order_id, "status": status}
    with SessionLocal() as session:
        rule = NotificationRule(channel="whatsapp", config={"target": phone})
        session.add(rule)
        session.flush()
        outbox = NotificationOutbox(rule_id=rule.id, payload=payload)
        session.add(outbox)
        session.flush()
        session.add(
            AuditTenant(
                actor="system",
                action="whatsapp_notify",
                meta={"tenant": tenant, "msg_id": str(outbox.id)},
            )
        )
        session.commit()
    logger.info("whatsapp queued")
