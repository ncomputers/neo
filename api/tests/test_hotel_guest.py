"""Smoke tests for guest-facing room endpoints."""

import sys
import types
import uuid

import fakeredis.aioredis
from fastapi import APIRouter
from fastapi.testclient import TestClient

from api.app.db import engine  # noqa: E402
from api.app.main import SessionLocal, app  # noqa: E402
from api.app.models_tenant import (  # noqa: E402
    Category,
    MenuItem,
    NotificationOutbox,
    Room,
)


client = TestClient(app)


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    global _orig_metrics, _orig_support
    _orig_metrics = sys.modules.get("api.app.metrics")
    _orig_support = sys.modules.get("api.app.routes_support")
    sys.modules.setdefault("api.app.metrics", types.SimpleNamespace(router=APIRouter()))
    sys.modules.setdefault("api.app.routes_support", types.SimpleNamespace(router=APIRouter()))


def seed():
    NotificationOutbox.__table__.drop(bind=engine, checkfirst=True)
    NotificationOutbox.__table__.create(bind=engine, checkfirst=True)
    with SessionLocal() as session:
        category = Category(name="Default", sort=1)
        session.add(category)
        session.flush()
        items = [
            MenuItem(
                category_id=category.id,
                name="Tea",
                price=10.0,
                is_veg=True,
                show_fssai=True,
            ),
            MenuItem(category_id=category.id, name="Coffee", price=20.0, is_veg=True),
        ]
        session.add_all(items)
        room = Room(code="R-101", qr_token="r-101")
        session.add(room)
        session.commit()
        return items[0].id


def test_room_menu_order_cleaning():
    item_id = seed()

    resp = client.get("/h/R-101/menu")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert any(item["show_fssai"] for item in data["data"]["items"])

    resp = client.post(
        "/h/R-101/order",
        headers={"Idempotency-Key": uuid.uuid4().hex},
        json={"items": [{"item_id": item_id, "qty": 1}]},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = client.post("/h/R-101/request/cleaning")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def teardown_module():
    if _orig_metrics is not None:
        sys.modules["api.app.metrics"] = _orig_metrics
    else:
        del sys.modules["api.app.metrics"]
    if _orig_support is not None:
        sys.modules["api.app.routes_support"] = _orig_support
    else:
        del sys.modules["api.app.routes_support"]
