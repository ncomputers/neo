# menu.py
"""CRUD operations for menu categories and items with import/export helpers."""

from __future__ import annotations

import os
import uuid
from io import BytesIO
from typing import Dict

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook, load_workbook

from .schemas import Category, CategoryIn, Item, ItemIn

router = APIRouter()

# In-memory stores for categories and items used by the demo API
_categories: Dict[uuid.UUID, Category] = {}
_items: Dict[uuid.UUID, Item] = {}

IMAGE_DIR = os.path.join(os.path.dirname(__file__), "static", "images")
os.makedirs(IMAGE_DIR, exist_ok=True)


@router.post("/categories", response_model=Category)
def create_category(data: CategoryIn) -> Category:
    """Create a category and return the stored model."""

    cid = uuid.uuid4()
    category = Category(id=cid, **data.model_dump())
    _categories[cid] = category
    return category


@router.get("/categories", response_model=list[Category])
def list_categories() -> list[Category]:
    """Return all known categories."""

    return list(_categories.values())


@router.delete("/categories/{category_id}")
def delete_category(category_id: uuid.UUID) -> None:
    """Remove a category if present."""

    _categories.pop(category_id, None)


@router.post("/items", response_model=Item)
def create_item(data: ItemIn) -> Item:
    """Create a menu item and return it."""

    iid = uuid.uuid4()
    item = Item(id=iid, **data.model_dump())
    _items[iid] = item
    return item


@router.get("/items", response_model=list[Item])
def list_items(include_out_of_stock: bool = False) -> list[Item]:
    """Return items, optionally including out-of-stock ones."""

    values = _items.values()
    if not include_out_of_stock:
        values = [i for i in values if i.in_stock]
    return list(values)


@router.get("/items/export")
def export_items() -> StreamingResponse:
    """Export current items to an Excel file."""

    wb = Workbook()
    ws = wb.active
    ws.append(["name", "price", "category", "in_stock", "show_fssai_icon"])
    for item in _items.values():
        cat = _categories.get(item.category_id)
        ws.append([
            item.name,
            item.price,
            cat.name if cat else None,
            item.in_stock,
            item.show_fssai_icon,
        ])
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    headers = {"Content-Disposition": "attachment; filename=items.xlsx"}
    return StreamingResponse(
        buffer,
        media_type="application/vnd.ms-excel",
        headers=headers,
    )


@router.get("/items/{item_id}", response_model=Item)
def get_item(item_id: uuid.UUID) -> Item:
    """Return a single item or 404 if missing."""

    item = _items.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.put("/items/{item_id}", response_model=Item)
def update_item(item_id: uuid.UUID, data: ItemIn) -> Item:
    """Update an item, storing price changes as pending."""

    stored = _items.get(item_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Item not found")
    update = data.model_dump()
    if update["price"] != stored.price:
        stored.pending_price = update["price"]  # Defer price update
        update.pop("price")
    for key, value in update.items():
        setattr(stored, key, value)
    return stored


@router.post("/items/apply-pending")
def apply_pending_prices() -> None:
    """Apply any pending price updates to live prices."""

    for item in _items.values():
        if item.pending_price is not None:
            item.price = item.pending_price
            item.pending_price = None


@router.delete("/items/{item_id}")
def delete_item(item_id: uuid.UUID) -> None:
    """Remove an item if present."""

    _items.pop(item_id, None)


@router.post("/items/{item_id}/image", response_model=Item)
def upload_image(item_id: uuid.UUID, file: UploadFile = File(...)) -> Item:
    """Persist an uploaded image for an item."""

    item = _items.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    filename = f"{item_id}_{file.filename}"
    path = os.path.join(IMAGE_DIR, filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    item.image_url = path
    return item


@router.post("/items/import")
def import_items(file: UploadFile = File(...)) -> int:
    """Import items from an uploaded Excel file."""

    wb = load_workbook(file.file)
    ws = wb.active
    count = 0
    for name, price, category_name in ws.iter_rows(min_row=2, values_only=True):
        cid = None
        if category_name:
            cid = next(
                (c.id for c in _categories.values() if c.name == category_name),
                None,
            )
            if cid is None:
                cid = uuid.uuid4()
                _categories[cid] = Category(id=cid, name=category_name)
        iid = uuid.uuid4()
        item = Item(id=iid, name=name, price=price, category_id=cid)
        _items[iid] = item
        count += 1  # Count rows processed
    return count


