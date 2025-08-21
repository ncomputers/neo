import uuid

from fastapi.testclient import TestClient
import fakeredis.aioredis

from api.app.main import SessionLocal, app
from api.app.models_tenant import Category, MenuItem, Room, NotificationOutbox
from api.app.db import engine
from api.app.auth import create_access_token

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
        item = MenuItem(
            category_id=category.id,
            name="Tea",
            price=10.0,
            is_veg=True,
        )
        session.add(item)
        room = Room(code="R1", qr_token="r1")
        session.add(room)
        session.commit()
        return item.id, room.id


def test_room_service_and_cleaning():
    item_id, room_id = seed()

    resp = client.get("/h/R1/menu")
    assert resp.status_code == 200
    assert resp.json()["data"]["items"][0]["id"] == item_id

    resp = client.post(
        "/h/R1/order",
        json={"items": [{"item_id": item_id, "qty": 1}]},
    )
    assert resp.status_code == 200

    resp = client.post("/h/R1/request/cleaning")
    assert resp.status_code == 200
    with SessionLocal() as session:
        outbox = (
            session.query(NotificationOutbox)
            .filter_by(event="housekeeping.requested")
            .one()
        )
        assert outbox.payload["room_code"] == "R1"

    token = create_access_token({"sub": "cleaner1", "role": "cleaner"})
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        f"/api/outlet/demo/housekeeping/room/{room_id}/start_clean",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["state"] == "PENDING_CLEANING"

    resp = client.post(
        "/h/R1/order", json={"items": [{"item_id": item_id, "qty": 1}]}
    )
    assert resp.status_code == 423

    resp = client.post(
        f"/api/outlet/demo/housekeeping/room/{room_id}/ready",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["state"] == "AVAILABLE"

    resp = client.post(
        "/h/R1/order",
        json={"items": [{"item_id": item_id, "qty": 1}]},
    )
    assert resp.status_code == 200
