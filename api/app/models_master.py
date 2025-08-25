from __future__ import annotations

"""Database models for the master schema."""

import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

from config import AcceptanceMode

Base = declarative_base()


class Tenant(Base):
    """Tenant metadata stored in the master database."""

    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    domain = Column(String, unique=True)
    logo_url = Column(String, nullable=True)
    primary_color = Column(String, nullable=True)
    gst_mode = Column(Boolean, nullable=False, default=False)
    inv_prefix = Column(String, nullable=True)
    inv_reset = Column(String, nullable=False, default="never")
    timezone = Column(String, nullable=True)
    licensed_tables = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="active")
    ema_window = Column(Integer, nullable=True)
    kds_sla_secs = Column(Integer, nullable=False, default=900)
    acceptance_mode = Column(String, nullable=False, default=AcceptanceMode.ITEM.value)
    sla_sound_alert = Column(Boolean, nullable=False, default=False)
    sla_color_alert = Column(Boolean, nullable=False, default=False)
    hide_out_of_stock_items = Column(Boolean, nullable=False, default=True)
    license_limits = Column(JSON, nullable=True)
    enable_hotel = Column(Boolean, nullable=False, default=False)
    enable_counter = Column(Boolean, nullable=False, default=False)
    subscription_expires_at = Column(DateTime, nullable=True)
    grace_period_days = Column(Integer, nullable=False, default=7)
    retention_days_customers = Column(Integer, nullable=True)
    retention_days_outbox = Column(Integer, nullable=True)
    maintenance_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SyncOutbox(Base):
    """Events queued for sync when the cloud API is unreachable."""

    __tablename__ = "sync_outbox"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    retries = Column(Integer, nullable=False, default=0)
    last_error = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class NotificationRule(Base):
    """Routing rule for outbound notifications."""

    __tablename__ = "notification_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel = Column(String, nullable=False)
    config = Column(JSON, nullable=True)


class NotificationOutbox(Base):
    """Queued notifications awaiting delivery."""

    __tablename__ = "notifications_outbox"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(
        UUID(as_uuid=True), ForeignKey("notification_rules.id"), nullable=False
    )
    payload = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="queued")
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    rule = relationship("NotificationRule")


class NotificationDLQ(Base):
    """Dead-letter queue for events that exceeded retry attempts."""

    __tablename__ = "notifications_dlq"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_id = Column(UUID(as_uuid=True), nullable=False)
    rule_id = Column(UUID(as_uuid=True), nullable=False)
    payload = Column(JSON, nullable=False)
    error = Column(String, nullable=False)
    failed_at = Column(DateTime, server_default=func.now())


__all__ = [
    "Base",
    "Tenant",
    "SyncOutbox",
    "NotificationRule",
    "NotificationOutbox",
    "NotificationDLQ",
]
