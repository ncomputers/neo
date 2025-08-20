"""Pydantic models for tenant-facing menu, ordering and billing."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class MenuItemOut(BaseModel):
    """Menu item details returned to guests."""

    id: UUID
    name: str
    price: int
    category_id: Optional[UUID] = None
    in_stock: bool
    show_fssai_icon: bool
    image_url: Optional[str] = None


class OrderLineIn(BaseModel):
    """Input line for placing an order."""

    menu_item_id: UUID
    quantity: int = 1


class OrderLineOut(BaseModel):
    """Line item returned as part of an order."""

    menu_item_id: UUID
    quantity: int
    price: int


class OrderOut(BaseModel):
    """Order representation including line items."""

    id: UUID
    status: str
    items: List[OrderLineOut]
    created_at: datetime
    updated_at: datetime


class InvoiceItemOut(BaseModel):
    """Single line item on an invoice."""

    name: str
    quantity: int
    price: int
    gst_rate: Optional[int] = None


class InvoiceOut(BaseModel):
    """Invoice details with line items."""

    id: UUID
    number: str
    total: int
    items: List[InvoiceItemOut]


class PaymentIn(BaseModel):
    """Input schema for recording a payment."""

    method: str
    amount: int


__all__ = [
    "MenuItemOut",
    "OrderLineIn",
    "OrderLineOut",
    "OrderOut",
    "InvoiceItemOut",
    "InvoiceOut",
    "PaymentIn",
]
