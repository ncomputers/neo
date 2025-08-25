import asyncio
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

import api.app.routes_orders_batch as batch
from api.app.main import app

client = TestClient(app)


def setup_module():
    batch._processed_ops.clear()


def test_duplicate_op_ids_dedup(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(batch, "get_engine", lambda tenant_id: engine)

    calls = []

    async def fake_create_order(session, table_code, lines):
        calls.append((table_code, lines))
        return 100 + len(calls)

    monkeypatch.setattr(batch.orders_repo_sql, "create_order", fake_create_order)

    op_id = str(uuid.uuid4())
    payload = {
        "orders": [
            {
                "op_id": op_id,
                "table_code": "T1",
                "items": [{"item_id": "1", "qty": 1}],
            }
        ]
    }
    resp1 = client.post("/api/outlet/tenant/orders/batch", json=payload)
    assert resp1.status_code == 200
    resp2 = client.post("/api/outlet/tenant/orders/batch", json=payload)
    assert resp2.status_code == 200
    assert resp1.json()["data"]["order_ids"]
    assert resp2.json()["data"]["order_ids"] == []
    assert len(calls) == 1

    asyncio.get_event_loop().run_until_complete(engine.dispose())
