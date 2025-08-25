import sqlite3


def _plan(sql: str, conn: sqlite3.Connection) -> str:
    cur = conn.execute(f"EXPLAIN QUERY PLAN {sql}")
    return " ".join(row[-1] for row in cur.fetchall())


def test_orders_index_used():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, status TEXT, created_at TEXT)"
    )
    conn.execute(
        "CREATE INDEX ix_orders_status_created_at ON orders " "(status, created_at)"
    )
    plan = _plan(
        "SELECT * FROM orders WHERE status='new' AND created_at>'2021-01-01'",
        conn,
    )
    assert "ix_orders_status_created_at" in plan


def test_order_items_index_used():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE order_items (" "id INTEGER PRIMARY KEY, order_id INTEGER)"
    )
    conn.execute("CREATE INDEX ix_order_items_order_id ON order_items (order_id)")
    plan = _plan("SELECT * FROM order_items WHERE order_id=1", conn)
    assert "ix_order_items_order_id" in plan


def test_invoices_index_used():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE invoices ("
        "id INTEGER PRIMARY KEY, created_at TEXT, tenant_id INTEGER)"
    )
    conn.execute(
        "CREATE INDEX ix_invoices_created_at_tenant_id ON invoices "
        "(created_at, tenant_id)"
    )
    plan = _plan(
        "SELECT * FROM invoices WHERE created_at>'2021-01-01' AND tenant_id=1",
        conn,
    )
    assert "ix_invoices_created_at_tenant_id" in plan


def test_payments_index_used():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE payments ("
        "id INTEGER PRIMARY KEY, invoice_id INTEGER, created_at TEXT)"
    )
    conn.execute(
        "CREATE INDEX ix_payments_invoice_id_created_at ON payments "
        "(invoice_id, created_at)"
    )
    plan = _plan(
        "SELECT * FROM payments WHERE invoice_id=1 AND " "created_at>'2021-01-01'",
        conn,
    )
    assert "ix_payments_invoice_id_created_at" in plan


def test_audit_tenant_index_used():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE audit_tenant (" "id INTEGER PRIMARY KEY, created_at TEXT)"
    )
    conn.execute("CREATE INDEX ix_audit_tenant_created_at ON audit_tenant (created_at)")
    plan = _plan(
        "SELECT * FROM audit_tenant WHERE created_at>'2021-01-01'",
        conn,
    )
    assert "ix_audit_tenant_created_at" in plan
