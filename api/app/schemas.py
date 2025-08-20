from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CategoryIn(BaseModel):
    name: str


class Category(CategoryIn):
    id: UUID


class ItemIn(BaseModel):
    name: str
    price: int
    category_id: Optional[UUID] = None
    in_stock: bool = True
    show_fssai_icon: bool = False


class Item(ItemIn):
    id: UUID
    image_url: Optional[str] = None
    pending_price: Optional[int] = None
