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
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
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
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


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
    modifiers = Column(JSON, nullable=False, server_default="[]")
    combos = Column(JSON, nullable=False, server_default="[]")
    dietary = Column(JSON, nullable=False, server_default="[]", default=list)
    allergens = Column(JSON, nullable=False, server_default="[]", default=list)

    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class TenantMeta(Base):
    """Tenant metadata including a menu version for cache busting."""

    __tablename__ = "tenant_meta"

    id = Column(Integer, primary_key=True, default=1)
    menu_version = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TableStatus(enum.Enum):
    """Lifecycle states for a dining table."""

    AVAILABLE = "available"
    OCCUPIED = "occupied"
    PENDING_CLEANING = "pending_cleaning"
    LOCKED = "locked"


class OrderStatus(enum.Enum):
    """Possible states for an order."""

    NEW = "new"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    SERVED = "served"


class Table(Base):
    """Dining tables mapped to QR tokens."""

    __tablename__ = "tables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    qr_token = Column(String, unique=True, nullable=True)
    status = Column(Enum(TableStatus), nullable=False, default=TableStatus.AVAILABLE)
    state = Column(String, nullable=False, default="AVAILABLE")
    pos_x = Column(Integer, nullable=False, server_default="0", default=0)
    pos_y = Column(Integer, nullable=False, server_default="0", default=0)
    label = Column(Text, nullable=True)
    last_cleaned_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class Room(Base):
    """Hotel rooms mapped to QR tokens."""

    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    qr_token = Column(String, unique=True, nullable=True)
    state = Column(String, nullable=False, default="AVAILABLE")
    last_cleaned_at = Column(DateTime(timezone=True), nullable=True)


class RoomOrder(Base):
    """Room service orders."""

    __tablename__ = "room_orders"

    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    status = Column(String, nullable=False)
    placed_at = Column(DateTime(timezone=True), nullable=True)
    served_at = Column(DateTime(timezone=True), nullable=True)


class RoomOrderItem(Base):
    """Line items for room service orders."""

    __tablename__ = "room_order_items"

    id = Column(Integer, primary_key=True)
    room_order_id = Column(Integer, ForeignKey("room_orders.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    name_snapshot = Column(String, nullable=False)
    price_snapshot = Column(Numeric(10, 2), nullable=False)
    qty = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    mods_snapshot = Column(JSON, nullable=False, server_default="[]")


class Order(Base):
    """Orders placed from a table."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False)
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
    mods_snapshot = Column(JSON, nullable=False, server_default="[]")


class Invoice(Base):
    """Invoices generated for groups of orders."""

    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    order_group_id = Column(Integer, nullable=False)
    number = Column(String, unique=True, nullable=False)
    bill_json = Column(JSON, nullable=False)
    gst_breakup = Column(JSON, nullable=True)
    tip = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    total = Column(Numeric(10, 2), nullable=False)
    settled = Column(Boolean, nullable=False, default=False)
    settled_at = Column(DateTime(timezone=True), nullable=True)
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
    is_stackable = Column(Boolean, nullable=False, default=False)
    max_discount = Column(Numeric(10, 2), nullable=True)


class Customer(Base):
    """End customers."""

    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    allow_analytics = Column(Boolean, nullable=False, default=False)
    allow_wa = Column(Boolean, nullable=False, default=False)


class Counter(Base):
    """Sales counters identified by QR tokens."""

    __tablename__ = "counters"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    qr_token = Column(String, unique=True, nullable=False)


class CounterOrderStatus(enum.Enum):
    """Lifecycle states for a takeaway counter order."""

    PLACED = "placed"
    READY = "ready"
    DELIVERED = "delivered"


class CounterOrder(Base):
    """Orders placed at a counter."""

    __tablename__ = "counter_orders"

    id = Column(Integer, primary_key=True)
    counter_id = Column(Integer, ForeignKey("counters.id"), nullable=False)
    status = Column(Enum(CounterOrderStatus), nullable=False)
    placed_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)


class CounterOrderItem(Base):
    """Snapshot of items in a counter order."""

    __tablename__ = "counter_order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("counter_orders.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    name_snapshot = Column(String, nullable=False)
    price_snapshot = Column(Numeric(10, 2), nullable=False)
    qty = Column(Integer, nullable=False)
    mods_snapshot = Column(JSON, nullable=False, server_default="[]")


class EMAStat(Base):
    """Stores exponential moving average stats for alerts."""

    __tablename__ = "ema_stats"

    id = Column(Integer, primary_key=True)
    window_n = Column(Integer, nullable=False)
    ema_seconds = Column(Numeric(10, 4), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class AlertRule(Base):
    """Configurable alert rules for tenant events."""

    __tablename__ = "alerts_rules"

    id = Column(Integer, primary_key=True)
    event = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    target = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)


class NotificationOutbox(Base):
    """Queued notifications awaiting delivery."""

    __tablename__ = "notifications_outbox"

    id = Column(Integer, primary_key=True)
    event = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    channel = Column(String, nullable=False)
    target = Column(String, nullable=False)
    status = Column(String, nullable=False, default="queued")
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)


class NotificationDLQ(Base):
    """Dead-letter queue for permanently failed notifications."""

    __tablename__ = "notifications_dlq"

    id = Column(Integer, primary_key=True)
    original_id = Column(Integer, nullable=False)
    event = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    target = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    error = Column(String, nullable=False)
    failed_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditTenant(Base):
    """Audit log for tenant actions."""

    __tablename__ = "audit_tenant"

    id = Column(Integer, primary_key=True)
    at = Column(DateTime(timezone=True), server_default=func.now())
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    meta = Column(JSON, nullable=True)


class Staff(Base):
    """Outlet staff able to authenticate via a numeric PIN."""

    __tablename__ = "staff"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    pin_hash = Column(String, nullable=False)
    pin_set_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    active = Column(Boolean, nullable=False, default=True)


class ApiKey(Base):
    """API keys for third-party integrations."""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String, nullable=False, unique=True)
    scopes = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SalesRollup(Base):
    """Daily precomputed sales aggregates."""

    __tablename__ = "sales_rollup"

    tenant_id = Column(String, primary_key=True)
    d = Column(Date, primary_key=True)
    orders = Column(Integer, nullable=False, default=0, server_default="0")
    sales = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    tax = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    tip = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    modes_json = Column(JSON, nullable=False, default=dict, server_default="{}")


class InvoiceCounter(Base):
    """Counters for generating sequential invoice numbers."""

    __tablename__ = "invoice_counters"

    id = Column(Integer, primary_key=True)
    series = Column(String, nullable=False, unique=True)
    current = Column(Integer, nullable=False, default=0)


__all__ = [
    "Base",
    "Category",
    "MenuItem",
    "TableStatus",
    "OrderStatus",
    "Table",
    "Room",
    "RoomOrder",
    "RoomOrderItem",
    "Order",
    "OrderItem",
    "Invoice",
    "Payment",
    "Coupon",
    "Customer",
    "Counter",
    "CounterOrderStatus",
    "CounterOrder",
    "CounterOrderItem",
    "EMAStat",
    "AlertRule",
    "NotificationOutbox",
    "NotificationDLQ",
    "AuditTenant",
    "Staff",
    "ApiKey",
    "SalesRollup",
    "InvoiceCounter",
    "TenantMeta",
]
