from __future__ import annotations

"""Tenant-specific database models such as menu and ordering tables."""

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

Base = declarative_base()


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
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
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


class OrderStatus(enum.Enum):
    """States for an order lifecycle."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Order(Base):
    """Customer order placed for a table session."""

    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("table_sessions.id"), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class OrderItem(Base):
    """Line items belonging to an order."""

    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    menu_item_id = Column(UUID(as_uuid=True), ForeignKey("menu_items.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    price = Column(Integer, nullable=False)


class Invoice(Base):
    """Generated invoice for a completed order."""

    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    number = Column(String, nullable=False)
    total = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class InvoiceItem(Base):
    """Line items belonging to an invoice."""

    __tablename__ = "invoice_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    gst_rate = Column(Integer, nullable=True)


__all__ = [
    "Base",
    "Category",
    "MenuItem",
    "TableStatus",
    "Table",
    "TableSession",
    "OrderStatus",
    "Order",
    "OrderItem",
    "Invoice",
    "InvoiceItem",
]
