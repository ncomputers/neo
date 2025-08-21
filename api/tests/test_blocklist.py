import asyncio
import os
import pathlib
import sqlite3
import sys

import fakeredis.aioredis
from fastapi.testclient import TestClient

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from api.app.main import app, tables
from api.app.hooks import order_rejection
from api.app.security.blocklist import add_rejection, is_blocked, block_ip, clear_ip
from api.app.repos_sqlalchemy import orders_repo_sql


os.environ.setdefault(
    "POSTGRES_TENANT_DSN_TEMPLATE", "sqlite+aiosqlite:///tenant_{tenant_id}.db"
)

conn = sqlite3.connect("tenant_demo.db")
conn.execute(
    "CREATE TABLE IF NOT EXISTS menu_categories (id INTEGER PRIMARY KEY, name TEXT, sort INTEGER)"
)
conn.execute(
    "CREATE TABLE IF NOT EXISTS menu_items (id INTEGER PRIMARY KEY, category_id INTEGER, name TEXT, price REAL, is_veg BOOLEAN, gst_rate REAL, hsn_sac TEXT, show_fssai BOOLEAN, out_of_stock BOOLEAN)"
)
conn.execute(
    "CREATE TABLE IF NOT EXISTS tables (id INTEGER PRIMARY KEY, code TEXT, status TEXT)"
)
conn.execute(
    "CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, table_id INTEGER, status TEXT)"
)
conn.execute("DELETE FROM tables")
conn.execute("DELETE FROM orders")
if not conn.execute("SELECT 1 FROM menu_categories").fetchone():
    conn.execute("INSERT INTO menu_categories (id, name, sort) VALUES (1, 'Main', 1)")
    conn.execute(
        "INSERT INTO menu_items (id, category_id, name, price, is_veg, gst_rate, hsn_sac, show_fssai, out_of_stock) VALUES (1, 1, 'Item', 10.0, 0, NULL, NULL, 0, 0)"
    )
conn.execute("INSERT INTO tables (id, code, status) VALUES (1, 'T-001', 'available')")
conn.commit()
conn.close()


async def _list_active_stub(session):  # pragma: no cover - simple stub
    return []


orders_repo_sql.list_active = _list_active_stub


@app.post("/g/echo")
async def _echo():  # pragma: no cover - simple test helper
    return {"ok": True}


def test_blocklist_helpers():
    redis = fakeredis.aioredis.FakeRedis()
    ip = "1.2.3.4"

    async def flow():
        assert await add_rejection(redis, ip) == 1
        assert await add_rejection(redis, ip) == 2
        assert not await is_blocked(redis, ip)
        await block_ip(redis, ip, ttl=10)
        assert await is_blocked(redis, ip)
        await clear_ip(redis, ip)
        assert not await is_blocked(redis, ip)
        assert await redis.exists(f"rej:ip:{ip}") == 0

    asyncio.run(flow())


def test_guest_block_after_rejections():
    redis = fakeredis.aioredis.FakeRedis()
    app.state.redis = redis
    client = TestClient(app)

    tables.clear()
    for i in range(3):
        client.post("/tables/t1/cart", json={"item": "c", "price": 1.0, "quantity": 1})
        client.post("/tables/t1/order")
        client.post(f"/orders/t1/{i}/reject")

    resp = client.post("/g/echo")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "SUB_403"

def test_block_after_three_manual_rejections():
    redis = fakeredis.aioredis.FakeRedis()
    app.state.redis = redis
    client = TestClient(app)

    async def _simulate():
        for _ in range(3):
            await order_rejection.on_rejected("testclient", redis)
    asyncio.run(_simulate())

    resp = client.post("/g/echo")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "SUB_403"

