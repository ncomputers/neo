from __future__ import annotations

"""Database models for the master schema."""

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

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
    invoice_prefix = Column(String, nullable=True)
    invoice_reset = Column(String, nullable=False, default="never")
    ema_window = Column(Integer, nullable=True)
    acceptance_mode = Column(String, nullable=False, default=AcceptanceMode.ITEM.value)
    sla_sound_alert = Column(Boolean, nullable=False, default=False)
    sla_color_alert = Column(Boolean, nullable=False, default=False)
    hide_out_of_stock_items = Column(Boolean, nullable=False, default=True)
    license_limits = Column(JSON, nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)
    grace_period_days = Column(Integer, nullable=False, default=7)
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


__all__ = ["Base", "Tenant", "SyncOutbox"]
