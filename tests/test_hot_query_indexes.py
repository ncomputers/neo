import datetime as dt

import sqlalchemy as sa

from api.app.db import SessionLocal, engine
from api.app.models_tenant import (
    AuditTenant,
    Invoice,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
)


def test_explain_uses_hot_indexes():
    with SessionLocal() as session:
        order = Order(
            table_id=1,
            status=OrderStatus.NEW,
            placed_at=dt.datetime.utcnow(),
        )
        session.add(order)
        session.flush()

        invoice = Invoice(
            order_group_id=1,
            number="INV-1",
            bill_json={},
            total=100,
            created_at=dt.datetime.utcnow(),
        )
        session.add(invoice)
        session.flush()

        payment = Payment(
            invoice_id=invoice.id,
            mode="cash",
            amount=100,
            created_at=dt.datetime.utcnow(),
        )
        session.add(payment)
        session.add(
            OrderItem(
                order_id=order.id,
                item_id=1,
                name_snapshot="Item",
                price_snapshot=10,
                qty=1,
                status="new",
            )
        )
        session.add(
            AuditTenant(
                actor="sys",
                action="test",
                at=dt.datetime.utcnow(),
            )
        )
        session.commit()
        order_id = order.id
        invoice_id = invoice.id

    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_invoices_created_at "
                "ON invoices (created_at)"
            )
        )
        conn.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_payments_invoice_id_created_at "
                "ON payments (invoice_id, created_at)"
            )
        )
        conn.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_orders_status_placed_at "
                "ON orders (status, placed_at)"
            )
        )
        conn.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_order_items_order_id "
                "ON order_items (order_id)"
            )
        )
        conn.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_audit_tenant_at " "ON audit_tenant (at)"
            )
        )

        plans = [
            conn.execute(
                sa.text(
                    "EXPLAIN QUERY PLAN SELECT * FROM invoices WHERE created_at > :ts"
                ),
                {"ts": "2000-01-01"},
            ).fetchall(),
            conn.execute(
                sa.text(
                    "EXPLAIN QUERY PLAN SELECT * FROM payments "
                    "WHERE invoice_id = :iid AND created_at > :ts"
                ),
                {"iid": invoice_id, "ts": "2000-01-01"},
            ).fetchall(),
            conn.execute(
                sa.text(
                    "EXPLAIN QUERY PLAN SELECT * FROM orders "
                    "WHERE status = :st AND placed_at > :ts"
                ),
                {"st": OrderStatus.NEW.value, "ts": "2000-01-01"},
            ).fetchall(),
            conn.execute(
                sa.text(
                    "EXPLAIN QUERY PLAN SELECT * FROM order_items "
                    "WHERE order_id = :oid"
                ),
                {"oid": order_id},
            ).fetchall(),
            conn.execute(
                sa.text("EXPLAIN QUERY PLAN SELECT * FROM audit_tenant WHERE at > :ts"),
                {"ts": "2000-01-01"},
            ).fetchall(),
        ]
        names = [
            "ix_invoices_created_at",
            "ix_payments_invoice_id_created_at",
            "ix_orders_status_placed_at",
            "ix_order_items_order_id",
            "ix_audit_tenant_at",
        ]
        for plan, name in zip(plans, names):
            assert any(name in row[3] for row in plan)
