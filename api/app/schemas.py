# schemas.py
"""Pydantic models used by the demo API."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CategoryIn(BaseModel):
    """Payload schema for creating a category."""

    name: str


class Category(CategoryIn):
    """Category returned in API responses."""

    id: UUID


class ItemIn(BaseModel):
    """Payload schema for creating an item."""

    name: str
    price: int
    category_id: Optional[UUID] = None
    in_stock: bool = True
    show_fssai_icon: bool = False


class Item(ItemIn):
    """Item returned in API responses."""

    id: UUID
    image_url: Optional[str] = None
    pending_price: Optional[int] = None
