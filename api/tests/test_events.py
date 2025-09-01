# test_events.py
import pathlib
import sys
import time

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

import fakeredis.aioredis
from fastapi.testclient import TestClient

from api.app.events import ALERTS, EMA_UPDATES, REPORTS
from api.app.main import app

app.state.redis = fakeredis.aioredis.FakeRedis()


def _wait_for(condition, timeout: float = 1.0) -> bool:
    """Poll ``condition`` until True or timeout expires."""

    start = time.time()
    while time.time() - start < timeout:
        if condition():
            return True
        time.sleep(0.01)
    return False


def test_order_event_dispatch():
    ALERTS.clear()
    item = {"item": "Tea", "price": 5.0, "quantity": 1}
    with TestClient(app) as client:
        client.post("/tables/10/cart", json=item)
        client.post("/tables/10/order")
        assert _wait_for(lambda: len(ALERTS) == 1)
    assert ALERTS[0]["table_id"] == "10"


def test_payment_verified_event_dispatch():
    EMA_UPDATES.clear()
    with TestClient(app) as client:
        tenant_id = client.post(
            "/tenants", params={"name": "t", "licensed_tables": 1}
        ).json()["data"]["tenant_id"]
        client.post(f"/tenants/{tenant_id}/subscription/renew")
        assert _wait_for(lambda: len(EMA_UPDATES) == 1)
    assert EMA_UPDATES[0]["tenant_id"] == tenant_id


def test_table_cleaned_event_dispatch():
    REPORTS.clear()
    with TestClient(app) as client:
        client.post("/tables/55/mark-clean")
        assert _wait_for(lambda: len(REPORTS) == 1)
    assert REPORTS[0]["table_id"] == "55"
