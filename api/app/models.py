# models.py

"""Database models for the master schema."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

from config import AcceptanceMode


Base = declarative_base()


class Tenant(Base):
    """Tenant metadata stored in the master database.

    The table stores basic branding information, domain mappings and a set of
    configurable settings used during onboarding. ``license_limits`` can be
    utilised by application logic to enforce per-table licensing counts.
    """

    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    domain = Column(String, unique=True)
    logo_url = Column(String, nullable=True)
    primary_color = Column(String, nullable=True)
    gst_mode = Column(Boolean, nullable=False, default=False)
    invoice_prefix = Column(String, nullable=True)
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


class Category(Base):
    """Menu item categories."""

    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)


class MenuItem(Base):
    """Individual menu items."""

    __tablename__ = "menu_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    pending_price = Column(Integer, nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    in_stock = Column(Boolean, nullable=False, default=True)
    show_fssai_icon = Column(Boolean, nullable=False, default=False)
    image_url = Column(String, nullable=True)


__all__ = ["Base", "Tenant", "Category", "MenuItem"]


class TableStatus(enum.Enum):
    """Lifecycle states for a dining table."""

    AVAILABLE = "available"
    OCCUPIED = "occupied"
    PENDING_CLEANING = "pending_cleaning"
    LOCKED = "locked"


class Table(Base):
    """Physical dining table mapped to a static QR code."""

    __tablename__ = "tables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    qr_code = Column(String, nullable=True)
    status = Column(Enum(TableStatus), default=TableStatus.AVAILABLE, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TableSession(Base):
    """Session model allowing a shared cart per table."""

    __tablename__ = "table_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_id = Column(UUID(as_uuid=True), ForeignKey("tables.id"), nullable=False)
    cart = Column(JSON, nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    settled_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    call_waiter = Column(Boolean, default=False, nullable=False)
    call_water = Column(Boolean, default=False, nullable=False)
    call_bill = Column(Boolean, default=False, nullable=False)
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


__all__ = [
    "Base",
    "Tenant",
    "Table",
    "TableSession",
    "TableStatus",
    "SyncOutbox",
]
