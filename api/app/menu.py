# menu.py

"""Database-backed menu management with import/export helpers."""

from __future__ import annotations

import os
import uuid
from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook, load_workbook
from sqlalchemy import select

from .db import SessionLocal
from .models_tenant import Category as CategoryModel, MenuItem as MenuItemModel
from .schemas import Category, CategoryIn, Item, ItemIn
from .utils.responses import ok

router = APIRouter()


def _category_to_schema(cat: CategoryModel) -> Category:
    return Category(id=cat.id, name=cat.name)


def _item_to_schema(item: MenuItemModel) -> Item:
    return Item(
        id=item.id,
        name=item.name,
        price=item.price,
        category_id=item.category_id,
        in_stock=item.in_stock,
        show_fssai_icon=item.show_fssai_icon,
        image_url=item.image_url,
        pending_price=item.pending_price,
    )


IMAGE_DIR = os.path.join(os.path.dirname(__file__), "static", "images")
os.makedirs(IMAGE_DIR, exist_ok=True)


# Categories


@router.post("/categories")
def create_category(data: CategoryIn) -> dict:
    """Create a new category and return it."""

    cid = uuid.uuid4()
    category = Category(id=cid, **data.model_dump())
    _categories[cid] = category
    return ok(category)



@router.get("/categories")
def list_categories() -> dict:
    """Return all categories."""

    return ok(list(_categories.values()))



@router.delete("/categories/{category_id}")
def delete_category(category_id: uuid.UUID) -> dict:
    """Delete a category if it exists."""

    _categories.pop(category_id, None)
    return ok(None)


# Menu Items


@router.post("/items")
def create_item(data: ItemIn) -> dict:
    """Create a menu item."""

    iid = uuid.uuid4()
    item = Item(id=iid, **data.model_dump())
    _items[iid] = item
    return ok(item)


@router.get("/items")
def list_items(include_out_of_stock: bool = False) -> dict:
    """List items, optionally including out-of-stock ones."""

    values = _items.values()
    if not include_out_of_stock:
        values = [i for i in values if i.in_stock]
    return ok(list(values))


# Import/Export


@router.get("/items/export")
def export_items() -> StreamingResponse:
    """Export current items to an Excel sheet."""
    wb = Workbook()
    ws = wb.active
    ws.append(["name", "price", "category", "in_stock", "show_fssai_icon"])
    with SessionLocal() as session:
        stmt = (
            select(MenuItemModel, CategoryModel)
            .join(CategoryModel, MenuItemModel.category_id == CategoryModel.id, isouter=True)
        )
        for item, cat in session.execute(stmt):
            ws.append(
                [
                    item.name,
                    item.price,
                    cat.name if cat else None,
                    item.in_stock,
                    item.show_fssai_icon,
                ]
            )
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    headers = {"Content-Disposition": "attachment; filename=items.xlsx"}
    return StreamingResponse(
        buffer,
        media_type="application/vnd.ms-excel",
        headers=headers,
    )


@router.post("/items/import")
def import_items(file: UploadFile = File(...)) -> dict:
    """Import items from an uploaded Excel sheet."""
    wb = load_workbook(file.file)
    ws = wb.active
    count = 0
    for name, price, category_name in ws.iter_rows(min_row=2, values_only=True):
        # iterate over rows creating categories/items as needed
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
        count += 1
    return ok(count)



@router.get("/items/{item_id}")
def get_item(item_id: uuid.UUID) -> dict:
    """Fetch a single item by ID."""

    item = _items.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return ok(item)



@router.put("/items/{item_id}")
def update_item(item_id: uuid.UUID, data: ItemIn) -> dict:
    """Update an item; price changes are staged as pending."""

    stored = _items.get(item_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Item not found")
    update = data.model_dump()
    if update["price"] != stored.price:
        stored.pending_price = update["price"]  # pending price update
        update.pop("price")
    for key, value in update.items():
        setattr(stored, key, value)
    return ok(stored)



@router.post("/items/apply-pending")
def apply_pending_prices() -> dict:
    """Apply any staged price updates."""
    with SessionLocal() as session:
        items = session.scalars(
            select(MenuItemModel).where(MenuItemModel.pending_price.is_not(None))
        ).all()
        for item in items:
            item.price = item.pending_price
            item.pending_price = None
    return ok(None)



@router.delete("/items/{item_id}")
def delete_item(item_id: uuid.UUID) -> dict:
    """Remove an item if present."""

    _items.pop(item_id, None)
    return ok(None)



# Images


@router.post("/items/{item_id}/image")
def upload_image(item_id: uuid.UUID, file: UploadFile = File(...)) -> dict:
    """Attach an image to an item by saving the uploaded file."""

    item = _items.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    filename = f"{item_id}_{file.filename}"
    path = os.path.join(IMAGE_DIR, filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    item.image_url = path
    return ok(item)

