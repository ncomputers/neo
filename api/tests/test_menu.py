# test_menu.py
import pathlib
import sys
import tempfile
from io import BytesIO

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
from openpyxl import Workbook
import fakeredis.aioredis

from api.app.main import app
from api.app.db import SessionLocal
from api.app.models_tenant import Category as CategoryModel, MenuItem as MenuItemModel

client = TestClient(app, raise_server_exceptions=False)


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()


def setup_function() -> None:
    with SessionLocal() as session:
        session.query(MenuItemModel).delete()
        session.query(CategoryModel).delete()
        session.commit()


def test_category_and_item_crud():
    cat = client.post("/menu/categories", json={"name": "Drinks"}).json()
    assert client.get("/menu/categories").json()[0]["name"] == "Drinks"
    item = client.post(
        "/menu/items",
        json={"name": "Tea", "price": 10, "category_id": cat["id"]},
    ).json()
    assert client.get("/menu/items").json()[0]["name"] == "Tea"
    upd = client.put(
        f"/menu/items/{item['id']}",
        json={"name": "Tea", "price": 12, "category_id": cat["id"]},
    ).json()
    assert upd["pending_price"] == 12
    client.post("/menu/items/apply-pending")
    assert client.get(f"/menu/items/{item['id']}").json()["price"] == 12
    client.delete(f"/menu/items/{item['id']}")
    assert client.get("/menu/items").json() == []
    client.delete(f"/menu/categories/{cat['id']}")
    assert client.get("/menu/categories").json() == []


def test_image_upload_and_export_import():
    cat = client.post("/menu/categories", json={"name": "Snacks"}).json()
    item = client.post(
        "/menu/items",
        json={"name": "Cake", "price": 20, "category_id": cat["id"]},
    ).json()
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        tmp.write(b"img")
        tmp.seek(0)
        resp = client.post(
            f"/menu/items/{item['id']}/image",
            files={"file": ("test.png", tmp, "image/png")},
        )
        assert resp.status_code == 200
    export = client.get("/menu/items/export")
    assert export.status_code == 200
    wb = Workbook()
    ws = wb.active
    ws.append(["name", "price", "category"])
    ws.append(["Cookie", 5, "Snacks"])
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    assert (
        client.post(
            "/menu/items/import",
            files={"file": ("items.xlsx", buf.getvalue(), "application/vnd.ms-excel")},
        ).status_code
        == 200
    )
    assert any(i["name"] == "Cookie" for i in client.get("/menu/items").json())
    # invalid row
    wb2 = Workbook()
    ws2 = wb2.active
    ws2.append(["name", "price", "category"])
    ws2.append(["Bad", "notnum", None])
    buf2 = BytesIO()
    wb2.save(buf2)
    buf2.seek(0)
    assert (
        client.post(
            "/menu/items/import",
            files={"file": ("bad.xlsx", buf2.getvalue(), "application/vnd.ms-excel")},
        ).status_code
        >= 400
    )
