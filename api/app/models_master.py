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
    enable_gateway = Column(Boolean, nullable=False, default=False)
    prep_sla_min = Column(Integer, nullable=False, default=15)
    eta_confidence = Column(String, nullable=False, default="p50")
    max_queue_factor = Column(
        Integer, nullable=False, default=16
    )  # store *10 to avoid float
    eta_enabled = Column(Boolean, nullable=False, default=False)
    subscription_expires_at = Column(DateTime, nullable=True)
    grace_period_days = Column(Integer, nullable=False, default=7)
    retention_days_customers = Column(Integer, nullable=True)
    retention_days_outbox = Column(Integer, nullable=True)
    maintenance_until = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    purge_at = Column(DateTime, nullable=True)
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


class Plan(Base):
    """Available subscription plans."""

    __tablename__ = "plans"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    price_inr = Column(Integer, nullable=False)
    billing_interval = Column(String, nullable=False)
    max_tables = Column(Integer, nullable=False)
    features_json = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class Subscription(Base):
    """Tenant subscription record."""

    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    plan_id = Column(String, ForeignKey("plans.id"), nullable=False)
    status = Column(String, nullable=False, default="active")
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    trial_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SubscriptionEvent(Base):
    """Audit trail of subscription events."""

    __tablename__ = "subscription_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), nullable=False)
    type = Column(String, nullable=False)
    payload_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class BillingInvoice(Base):
    """Billing invoice for a tenant."""

    __tablename__ = "billing_invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    number = Column(String, nullable=False)
    amount_inr = Column(Integer, nullable=False)
    gst_inr = Column(Integer, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)
    pdf_url = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class TwoFactorSecret(Base):
    """TOTP secret hashes for owner/admin accounts."""

    __tablename__ = "twofactor_secrets"

    user = Column(String, primary_key=True)
    secret = Column(String, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class TwoFactorBackupCode(Base):
    """One-time backup codes for 2FA."""

    __tablename__ = "twofactor_backup_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user = Column(String, nullable=False, index=True)
    code_hash = Column(String, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class PrepStats(Base):
    """Per-item prep time percentiles aggregated nightly."""

    __tablename__ = "prep_stats"

    item_id = Column(String, primary_key=True)
    outlet_id = Column(Integer, primary_key=True)
    p50_s = Column(Integer, nullable=False)
    p80_s = Column(Integer, nullable=False)
    p95_s = Column(Integer, nullable=False)
    sample_n = Column(Integer, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SupportTicket(Base):
    """Owner support tickets stored in the master database."""

    __tablename__ = "support_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant = Column(String, nullable=True)
    subject = Column(String, nullable=False)
    body = Column(String, nullable=False)
    screenshots = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="open")
    created_at = Column(DateTime, server_default=func.now())


class FeedbackNPS(Base):
    """Net Promoter Score feedback from owners."""

    __tablename__ = "feedback_nps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant = Column(String, nullable=True)
    user = Column(String, nullable=True)
    score = Column(Integer, nullable=False)
    comment = Column(String, nullable=True)
    feature_request = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())


class Device(Base):
    """Registered staff devices."""

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    fingerprint = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now())


__all__ = [
    "Base",
    "Tenant",
    "SyncOutbox",
    "NotificationRule",
    "NotificationOutbox",
    "NotificationDLQ",
    "TwoFactorSecret",
    "TwoFactorBackupCode",
    "PrepStats",
    "SupportTicket",
    "FeedbackNPS",
    "Device",
]
