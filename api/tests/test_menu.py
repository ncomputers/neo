# test_menu.py
"""Tests for menu CRUD, image upload, and Excel import/export."""

import tempfile
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import Workbook

sys.path.append(str(Path(__file__).resolve().parents[2]))

from api.app.menu import router

app = FastAPI()
app.include_router(router, prefix="/menu")
client = TestClient(app)


def test_category_and_item_crud(tmp_path):
    cat = client.post("/menu/categories", json={"name": "Drinks"}).json()
    item = client.post(
        "/menu/items",
        json={"name": "Coffee", "price": 5, "category_id": cat["id"]},
    ).json()
    updated = client.put(
        f"/menu/items/{item['id']}",
        json={"name": "Coffee", "price": 6, "category_id": cat["id"]},
    ).json()
    assert updated["pending_price"] == 6
    client.post("/menu/items/apply-pending")
    assert client.get(f"/menu/items/{item['id']}").json()["price"] == 6


def test_image_upload(tmp_path):
    cat = client.post("/menu/categories", json={"name": "Snacks"}).json()
    item = client.post(
        "/menu/items",
        json={"name": "Pie", "price": 3, "category_id": cat["id"]},
    ).json()
    file_path = tmp_path / "image.txt"
    file_path.write_text("img")
    with file_path.open("rb") as f:
        resp = client.post(
            f"/menu/items/{item['id']}/image",
            files={"file": ("image.txt", f, "text/plain")},
        )
    assert resp.json()["image_url"]


def test_excel_import_export(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["name", "price", "category"])
    ws.append(["Tea", 2, "Drinks"])
    path = tmp_path / "items.xlsx"
    wb.save(path)
    with path.open("rb") as f:
        resp = client.post("/menu/items/import", files={"file": ("items.xlsx", f, "application/vnd.ms-excel")})
    assert resp.json() == 1
    resp = client.get("/menu/items/export")
    assert resp.headers["content-type"].startswith("application/vnd.ms-excel")
    assert resp.content
