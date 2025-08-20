"""Database models for the master schema.

This module currently defines the :class:`Tenant` model used to track
metadata for each onboarded tenant. Additional models may be added as the
project grows.
"""

from __future__ import annotations

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
