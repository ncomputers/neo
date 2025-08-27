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
        """
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
        """
    )

    now = datetime.utcnow()
    orders = [
        (1, 'new', now - timedelta(minutes=i), None, 10, None, 100.0)
        for i in range(50)
    ]
    orders.append((1, 'new', now, None, 20, None, 50.0))
    cur.executemany(
        "INSERT INTO orders (tenant_id, status, created_at, deleted_at, table_id, closed_at, total_amount) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        orders,
    )

    menu = [
        (1, 5, i, True, None, Json(['vegan']))
        for i in range(10)
    ]
    cur.executemany(
        "INSERT INTO menu_items (tenant_id, category_id, sort_order, is_active, deleted_at, dietary) VALUES (%s,%s,%s,%s,%s,%s)",
        menu,
    )

    webhooks = [
        (1, now + timedelta(minutes=i), 'pending')
        for i in range(5)
    ]
    cur.executemany(
        "INSERT INTO webhook_events (tenant_id, next_attempt_at, state) VALUES (%s,%s,%s)",
        webhooks,
    )

    cur.execute("ANALYZE")

    cur.close()
    conn.close()


def _plan(sql, params=None):
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("SET enable_seqscan=off")
    cur.execute(sql, params or ())
    plan = "\n".join(row[0] for row in cur.fetchall())
    cur.close()
    conn.close()
    return plan


def test_open_orders_by_table():
    plan = _plan(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE tenant_id=1 AND table_id=10 AND closed_at IS NULL AND deleted_at IS NULL ORDER BY created_at DESC"
    )
    assert "Index Scan" in plan and "idx_orders_tenant_table_open" in plan


def test_kds_status_window():
    plan = _plan(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE tenant_id=1 AND status='new' AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 5"
    )
    assert "Bitmap Index Scan" in plan or "Index Scan" in plan
    assert "idx_orders_tenant_status_created" in plan


def test_menu_category_active():
    plan = _plan(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM menu_items WHERE tenant_id=1 AND category_id=5 AND is_active = TRUE AND deleted_at IS NULL ORDER BY sort_order"
    )
    assert "Index Scan" in plan and "idx_menu_tenant_category_active" in plan


def test_dietary_filter():
    plan = _plan(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM menu_items WHERE tenant_id=1 AND coalesce(dietary, '[]'::jsonb) ? 'vegan'"
    )
    assert "Bitmap Index Scan" in plan or "Index Scan" in plan
    assert "gin_menu_dietary" in plan


def test_webhooks_due():
    plan = _plan(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM webhook_events WHERE tenant_id=1 AND state='pending' ORDER BY next_attempt_at LIMIT 1"
    )
    assert "Index Scan" in plan and "idx_webhooks_tenant_due" in plan


def test_orders_date_range_brin():
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("SET enable_seqscan=off")
    cur.execute(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE created_at > now() - interval '1 hour'"
    )
    plan = "\n".join(r[0] for r in cur.fetchall())
    cur.close()
    conn.close()
    assert "brin_orders_created" in plan


def test_partial_index_skips_deleted():
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (tenant_id, status, created_at, deleted_at, table_id, closed_at, total_amount) VALUES (1,'new',now(),NULL,30,NULL,10.0) RETURNING id")
    oid = cur.fetchone()[0]
    conn.commit()
    plan_live = _plan(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE tenant_id=1 AND table_id=30 AND closed_at IS NULL AND deleted_at IS NULL"
    )
    assert "idx_orders_tenant_table_open" in plan_live
    cur.execute("UPDATE orders SET deleted_at=now() WHERE id=%s", (oid,))
    conn.commit()
    plan_deleted = _plan(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE tenant_id=1 AND table_id=30 AND closed_at IS NULL AND deleted_at IS NOT NULL"
    )
    assert "idx_orders_tenant_table_open" not in plan_deleted
    cur.close()
    conn.close()
