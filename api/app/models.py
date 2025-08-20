"""Database models for the master schema.

This module currently defines the :class:`Tenant` model used to track
metadata for each onboarded tenant. Additional models may be added as the
project grows.
"""

from __future__ import annotations

import uuid

import enum

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
    license_limits = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


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


__all__ = [
    "Base",
    "Tenant",
    "Table",
    "TableSession",
    "TableStatus",
]
