# schemas.py

"""Pydantic models for API payloads and responses."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CategoryIn(BaseModel):
    """Input schema for creating a category."""

    name: str


class Category(CategoryIn):
    """Category representation returned from the API."""

    id: UUID


class ItemIn(BaseModel):
    """Input schema for creating or updating an item."""

    name: str
    price: int
    category_id: Optional[UUID] = None
    in_stock: bool = True
    show_fssai_icon: bool = False


class Item(ItemIn):
    """Item representation including database-generated fields."""

    id: UUID
    image_url: Optional[str] = None
    pending_price: Optional[int] = None
