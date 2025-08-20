"""Tenant-specific database models.

These models describe the per-tenant schema used by the application. They are
kept isolated from any application wiring so that they can be used in tests or
migrations independently."""

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
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class Category(Base):
    """Categories for menu items."""

    __tablename__ = "menu_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    sort = Column(Integer, nullable=False)


class MenuItem(Base):
    """Tenant-specific menu items."""

    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("menu_categories.id"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    is_veg = Column(Boolean, nullable=False, default=False)
    gst_rate = Column(Numeric(5, 2), nullable=True)
    hsn_sac = Column(String, nullable=True)
    show_fssai = Column(Boolean, nullable=False, default=False)
    out_of_stock = Column(Boolean, nullable=False, default=False)


class TableStatus(enum.Enum):
    """Lifecycle states for a dining table."""

    AVAILABLE = "available"
    OCCUPIED = "occupied"
    PENDING_CLEANING = "pending_cleaning"
    LOCKED = "locked"


class Table(Base):
    """Dining tables mapped to QR tokens."""

    __tablename__ = "tables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=True)
    qr_token = Column(String, unique=True, nullable=True)
    status = Column(Enum(TableStatus), nullable=False, default=TableStatus.AVAILABLE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Order(Base):
    """Orders placed from a table."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)
    status = Column(String, nullable=False)
    placed_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    ready_at = Column(DateTime(timezone=True), nullable=True)
    served_at = Column(DateTime(timezone=True), nullable=True)


class OrderItem(Base):
    """Line items belonging to an order."""

    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    name_snapshot = Column(String, nullable=False)
    price_snapshot = Column(Numeric(10, 2), nullable=False)
    qty = Column(Integer, nullable=False)
    status = Column(String, nullable=False)


class Invoice(Base):
    """Invoices generated for groups of orders."""

    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    order_group_id = Column(Integer, nullable=False)
    number = Column(String, unique=True, nullable=False)
    bill_json = Column(JSON, nullable=False)
    gst_breakup = Column(JSON, nullable=True)
    total = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Payment(Base):
    """Payments received for invoices."""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    mode = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    utr = Column(String, nullable=True)
    verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Coupon(Base):
    """Discount coupons."""

    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    percent = Column(Numeric(5, 2), nullable=True)
    flat = Column(Numeric(10, 2), nullable=True)
    active = Column(Boolean, nullable=False, default=True)


class Customer(Base):
    """End customers."""

    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)


class EMAStat(Base):
    """Stores exponential moving average stats for alerts."""

    __tablename__ = "ema_stats"

    id = Column(Integer, primary_key=True)
    window_n = Column(Integer, nullable=False)
    ema_seconds = Column(Numeric(10, 4), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditTenant(Base):
    """Audit log for tenant actions."""

    __tablename__ = "audit_tenant"

    id = Column(Integer, primary_key=True)
    at = Column(DateTime(timezone=True), server_default=func.now())
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    meta = Column(JSON, nullable=True)


__all__ = [
    "Base",
    "Category",
    "MenuItem",
    "TableStatus",
    "Table",
    "Order",
    "OrderItem",
    "Invoice",
    "Payment",
    "Coupon",
    "Customer",
    "EMAStat",
    "AuditTenant",
]
