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

from .db.master import SessionLocal
from .models import Category as CategoryModel, MenuItem as MenuItemModel
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

    with SessionLocal() as session:
        category = CategoryModel(id=uuid.uuid4(), name=data.name)
        session.add(category)
        session.commit()
        session.refresh(category)
        return ok(_category_to_schema(category))


@router.get("/categories")
def list_categories() -> dict:
    """Return all categories."""

    with SessionLocal() as session:
        cats = session.scalars(
            select(CategoryModel).order_by(CategoryModel.name)
        ).all()
        return ok([_category_to_schema(c) for c in cats])


@router.delete("/categories/{category_id}")
def delete_category(category_id: uuid.UUID) -> dict:
    """Delete a category if it exists."""

    with SessionLocal() as session:
        cat = session.get(CategoryModel, category_id)
        if cat:
            session.delete(cat)
            session.commit()
    return ok(None)


# Menu Items


@router.post("/items")
def create_item(data: ItemIn) -> dict:
    """Create a menu item."""

    with SessionLocal() as session:
        item = MenuItemModel(id=uuid.uuid4(), **data.model_dump())
        session.add(item)
        session.commit()
        session.refresh(item)
        return ok(_item_to_schema(item))


@router.get("/items")
def list_items(include_out_of_stock: bool = False) -> dict:
    """List items, optionally including out-of-stock ones."""

    with SessionLocal() as session:
        stmt = select(MenuItemModel).order_by(MenuItemModel.name)
        if not include_out_of_stock:
            stmt = stmt.where(MenuItemModel.in_stock)
        items = session.scalars(stmt).all()
        return ok([_item_to_schema(i) for i in items])


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
    with SessionLocal() as session:
        for name, price, category_name in ws.iter_rows(min_row=2, values_only=True):
            if not isinstance(price, (int, float)):
                raise HTTPException(status_code=400, detail="Invalid price")
            cid = None
            if category_name:
                cat = session.scalar(
                    select(CategoryModel).where(CategoryModel.name == category_name)
                )
                if cat is None:
                    cat = CategoryModel(id=uuid.uuid4(), name=category_name)
                    session.add(cat)
                cid = cat.id
            item = MenuItemModel(
                id=uuid.uuid4(), name=name, price=price, category_id=cid
            )
            session.add(item)
            count += 1
        session.commit()
    return ok(count)


@router.get("/items/{item_id}")
def get_item(item_id: uuid.UUID) -> dict:
    """Fetch a single item by ID."""

    with SessionLocal() as session:
        item = session.get(MenuItemModel, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return ok(_item_to_schema(item))


@router.put("/items/{item_id}")
def update_item(item_id: uuid.UUID, data: ItemIn) -> dict:
    """Update an item; price changes are staged as pending."""

    with SessionLocal() as session:
        item = session.get(MenuItemModel, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        update = data.model_dump()
        if update["price"] != item.price:
            item.pending_price = update["price"]
            update.pop("price")
        for key, value in update.items():
            setattr(item, key, value)
        session.commit()
        session.refresh(item)
        return ok(_item_to_schema(item))


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
        session.commit()
    return ok(None)


@router.delete("/items/{item_id}")
def delete_item(item_id: uuid.UUID) -> dict:
    """Remove an item if present."""

    with SessionLocal() as session:
        item = session.get(MenuItemModel, item_id)
        if item:
            session.delete(item)
            session.commit()
    return ok(None)


@router.post("/items/{item_id}/image")
def upload_image(item_id: uuid.UUID, file: UploadFile = File(...)) -> dict:
    """Attach an image to an item by saving the uploaded file."""

    with SessionLocal() as session:
        item = session.get(MenuItemModel, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        filename = f"{item_id}_{file.filename}"
        path = os.path.join(IMAGE_DIR, filename)
        with open(path, "wb") as f:
            f.write(file.file.read())
        item.image_url = path
        session.commit()
        session.refresh(item)
        return ok(_item_to_schema(item))
