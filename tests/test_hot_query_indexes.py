import pytest
import sqlalchemy as sa

from api.app.db import engine

pytestmark = pytest.mark.skipif(
    engine.dialect.name == "sqlite",
    reason="SQLite planner differs and skips index checks",
)


def test_explain_uses_hot_path_indexes() -> None:
    queries = [
        (
            "idx_inv_tenant_created",
            "EXPLAIN SELECT * FROM invoices "
            "WHERE tenant_id = 1 ORDER BY created_at DESC",
        ),
        (
            "idx_pay_invoice_created",
            "EXPLAIN SELECT * FROM payments "
            "WHERE invoice_id = 1 ORDER BY created_at DESC",
        ),
        (
            "idx_orders_tenant_status_created",
            "EXPLAIN SELECT * FROM orders "
            "WHERE tenant_id = 1 AND status = 'new' "
            "ORDER BY created_at DESC",
        ),
        (
            "idx_audit_tenant_created",
            "EXPLAIN SELECT * FROM audit_tenant "
            "WHERE tenant_id = 1 ORDER BY created_at DESC",
        ),
    ]
    with engine.begin() as conn:
        for name, sql in queries:
            plan = conn.execute(sa.text(sql)).fetchall()
            assert any(name in row[0] for row in plan)
