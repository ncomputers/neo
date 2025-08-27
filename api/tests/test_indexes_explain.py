from __future__ import annotations

import re
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import Json

DSN = "dbname=testdb user=postgres password=postgres host=localhost"


def setup_module(module):
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute(
        """
        DROP TABLE IF EXISTS orders, menu_items, webhook_events;
        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            tenant_id INT NOT NULL,
            status TEXT,
            created_at TIMESTAMPTZ NOT NULL,
            deleted_at TIMESTAMPTZ,
            table_id INT,
            closed_at TIMESTAMPTZ,
            total_amount NUMERIC
        );
        CREATE TABLE menu_items (
            id SERIAL PRIMARY KEY,
            tenant_id INT NOT NULL,
            category_id INT,
            sort_order INT,
            is_active BOOL,
            deleted_at TIMESTAMPTZ,
            dietary JSONB
        );
        CREATE TABLE webhook_events (
            id SERIAL PRIMARY KEY,
            tenant_id INT NOT NULL,
            next_attempt_at TIMESTAMPTZ,
            state TEXT
        );
        """,
    )

    cur.execute(
        """
        CREATE INDEX idx_orders_tenant_status_created
            ON orders (tenant_id, status, created_at DESC)
            INCLUDE (total_amount, table_id)
            WHERE deleted_at IS NULL;
        CREATE INDEX idx_orders_tenant_table_open
            ON orders (tenant_id, table_id, created_at DESC)
            WHERE closed_at IS NULL AND deleted_at IS NULL;
        CREATE INDEX brin_orders_created
            ON orders USING BRIN (created_at);
        CREATE INDEX idx_menu_tenant_category_active
            ON menu_items (tenant_id, category_id, sort_order)
            WHERE is_active = TRUE AND deleted_at IS NULL;
        CREATE INDEX gin_menu_dietary
            ON menu_items USING GIN ((coalesce(dietary, '[]'::jsonb)));
        CREATE INDEX idx_webhooks_tenant_due
            ON webhook_events (tenant_id, next_attempt_at)
            WHERE state = 'pending';
        """,
    )

    now = datetime.utcnow()
    orders = [
        (1, "new", now - timedelta(minutes=i), None, 10, None, 100.0)
        for i in range(50)
    ]
    orders.append((1, "new", now, None, 20, None, 50.0))
    cur.executemany(
        "INSERT INTO orders (tenant_id, status, created_at, deleted_at, table_id, closed_at, total_amount) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        orders,
    )

    menu = [
        (1, 5, i, True, None, Json(["vegan"]))
        for i in range(10)
    ]
    cur.executemany(
        "INSERT INTO menu_items (tenant_id, category_id, sort_order, is_active, deleted_at, dietary) VALUES (%s,%s,%s,%s,%s,%s)",
        menu,
    )

    webhooks = [
        (1, now + timedelta(minutes=i), "pending")
        for i in range(5)
    ]
    cur.executemany(
        "INSERT INTO webhook_events (tenant_id, next_attempt_at, state) VALUES (%s,%s,%s)",
        webhooks,
    )

    cur.execute("ANALYZE")

    cur.close()
    conn.close()


def _plan_stats(sql: str, params: tuple | None = None) -> tuple[str, int, float]:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("SET enable_seqscan=off")
    cur.execute(sql, params or ())
    lines = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    first = lines[0]
    plan = "\n".join(lines)
    m_cost = re.search(r"cost=(\d+\.\d+)\.\.(\d+\.\d+)", first)
    m_rows = re.search(r"actual time=[^)]* rows=(\d+)", first)
    cost = float(m_cost.group(2)) if m_cost else 0.0
    rows = int(m_rows.group(1)) if m_rows else 0
    return plan, rows, cost

def test_open_orders_by_table():
    plan, rows, cost = _plan_stats(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE tenant_id=1 AND table_id=10 AND closed_at IS NULL AND deleted_at IS NULL ORDER BY created_at DESC"
    )
    assert re.search(r"idx_orders_tenant_table_open", plan)
    assert 48 <= rows <= 52
    assert cost < 20


def test_kds_status_window():
    plan, rows, cost = _plan_stats(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE tenant_id=1 AND status='new' AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 5"
    )
    assert re.search(r"idx_orders_tenant_status_created", plan)
    assert 5 <= rows <= 6
    assert cost < 5


def test_menu_category_active():
    plan, rows, cost = _plan_stats(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM menu_items WHERE tenant_id=1 AND category_id=5 AND is_active = TRUE AND deleted_at IS NULL ORDER BY sort_order"
    )
    assert re.search(r"idx_menu_tenant_category_active", plan)
    assert 9 <= rows <= 11
    assert cost < 20


def test_dietary_filter():
    plan, rows, cost = _plan_stats(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM menu_items WHERE tenant_id=1 AND coalesce(dietary, '[]'::jsonb) ? 'vegan'"
    )
    assert re.search(r"gin_menu_dietary", plan)
    assert 9 <= rows <= 11
    assert cost < 25


def test_webhooks_due():
    plan, rows, cost = _plan_stats(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM webhook_events WHERE tenant_id=1 AND state='pending' ORDER BY next_attempt_at LIMIT 1"
    )
    assert re.search(r"idx_webhooks_tenant_due", plan)
    assert rows == 1
    assert cost < 5


def test_orders_date_range_brin():
    plan, rows, cost = _plan_stats(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE created_at > now() - interval '1 hour'"
    )
    assert re.search(r"brin_orders_created", plan)
    assert 50 <= rows <= 52
    assert cost < 25
