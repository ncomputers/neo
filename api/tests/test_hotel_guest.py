"""Smoke tests for guest-facing room endpoints."""

import sys
import types

import fakeredis.aioredis
from fastapi import APIRouter
from fastapi.testclient import TestClient

sys.modules.setdefault("api.app.metrics", types.SimpleNamespace(router=APIRouter()))

from api.app.main import app, SessionLocal
from api.app.models_tenant import Category, MenuItem, Room, NotificationOutbox
from api.app.db import engine

client = TestClient(app)


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()


def seed():
    NotificationOutbox.__table__.drop(bind=engine, checkfirst=True)
    NotificationOutbox.__table__.create(bind=engine, checkfirst=True)
    with SessionLocal() as session:
        category = Category(name="Default", sort=1)
        session.add(category)
        session.flush()
        items = [
            MenuItem(category_id=category.id, name="Tea", price=10.0, is_veg=True),
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
    assert resp.json()["ok"] is True

    resp = client.post(
        "/h/R-101/order",
        headers={"Idempotency-Key": "test"},
        json={"items": [{"item_id": item_id, "qty": 1}]},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = client.post("/h/R-101/request/cleaning")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
