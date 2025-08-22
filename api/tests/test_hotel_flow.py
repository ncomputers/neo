import uuid

import fakeredis.aioredis
from fastapi.testclient import TestClient

from api.app.main import app, SessionLocal
from api.app.models_tenant import Category, MenuItem, Room
from api.app.auth import create_access_token
from api.app import routes_hotel_housekeeping

client = TestClient(app)


def setup_module():
    app.state.redis = fakeredis.aioredis.FakeRedis()
    app.dependency_overrides[routes_hotel_housekeeping.get_tenant_id] = lambda: "demo"


def seed():
    with SessionLocal() as session:
        category = Category(name="Default", sort=1)
        session.add(category)
        session.flush()
        item = MenuItem(category_id=category.id, name="Tea", price=10.0, is_veg=True)
        session.add(item)
        room_code = "R" + uuid.uuid4().hex[:6]
        room_token = "r" + uuid.uuid4().hex[:6]
        room = Room(code=room_code, qr_token=room_token)
        session.add(room)
        session.commit()
        return item.id, room.id, room_code


def test_room_order_and_cleaning_cycle():
    item_id, room_id, room_code = seed()

    resp = client.get(f"/h/{room_code}/menu")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = client.post(
        f"/h/{room_code}/order",
        headers={"Idempotency-Key": uuid.uuid4().hex},
        json={"items": [{"item_id": item_id, "qty": 1}]},
    )
    assert resp.status_code == 200
    first_id = resp.json()["data"]["order_id"]
    assert resp.json()["ok"] is True
    assert first_id

    jwt = create_access_token({"sub": "cleaner1", "role": "cleaner"})
    headers = {"Authorization": f"Bearer {jwt}"}
    resp = client.post(f"/api/outlet/housekeeping/room/{room_id}/start_clean", headers=headers)
    assert resp.status_code == 200

    resp = client.post(
        f"/h/{room_code}/order",
        headers={"Idempotency-Key": uuid.uuid4().hex},
        json={"items": [{"item_id": item_id, "qty": 1}]},
    )
    assert resp.status_code == 423

    resp = client.post(f"/api/outlet/housekeeping/room/{room_id}/ready", headers=headers)
    assert resp.status_code == 200

    resp = client.post(
        f"/h/{room_code}/order",
        headers={"Idempotency-Key": uuid.uuid4().hex},
        json={"items": [{"item_id": item_id, "qty": 1}]},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
