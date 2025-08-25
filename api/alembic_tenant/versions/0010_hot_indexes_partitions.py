"""add hot-path indexes and optional partitions

Revision ID: 0010_hot_indexes_partitions
Revises: 0009_notifications_backoff_dlq
Create Date: 2025-05-05
"""

from __future__ import annotations

from datetime import date, timedelta

import sqlalchemy as sa
from alembic import op

revision: str = "0010_hot_indexes_partitions"
down_revision: str | None = "0009_notifications_backoff_dlq"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


INDEXES: list[tuple[str, str, list[str]]] = [
    ("invoices", "ix_invoices_created_at_tenant_id", ["created_at", "tenant_id"]),
    ("payments", "ix_payments_invoice_id_created_at", ["invoice_id", "created_at"]),
    ("orders", "ix_orders_status_created_at", ["status", "created_at"]),
    ("order_items", "ix_order_items_order_id", ["order_id"]),
    ("audit_tenant", "ix_audit_tenant_created_at", ["created_at"]),
]


def _create_monthly_partition(conn, table: str) -> None:
    if conn.dialect.name != "postgresql":
        return
    # skip if table is not partitioned
    check = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_partitioned_table pt "
            "JOIN pg_class c ON c.oid = pt.partrelid "
            "WHERE c.relname = :t"
        ),
        {"t": table},
    ).first()
    if not check:
        return
    today = date.today().replace(day=1)
    next_month = (today + timedelta(days=32)).replace(day=1)
    pname = f"{table}_{today:%Y_%m}"
    sql = f"""
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = '{pname}') THEN
        EXECUTE 'CREATE TABLE {pname} PARTITION OF {table} '
        'FOR VALUES FROM (''{today.isoformat()}''::date) '
        'TO (''{next_month.isoformat()}''::date)';
    END IF;
END $$;
"""  # nosec B608
    conn.execute(sa.text(sql))


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    for table, name, cols in INDEXES:
        if not insp.has_table(table):
            continue
        col_names = {c["name"] for c in insp.get_columns(table)}
        if not set(cols).issubset(col_names):
            continue
        index_names = {ix["name"] for ix in insp.get_indexes(table)}
        if name not in index_names:
            op.create_index(name, table, cols)
    _create_monthly_partition(conn, "invoices")
    _create_monthly_partition(conn, "payments")


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    for table, name, cols in INDEXES:
        if not insp.has_table(table):
            continue
        index_names = {ix["name"] for ix in insp.get_indexes(table)}
        if name in index_names:
            op.drop_index(name, table_name=table)
    # partitions are left in place intentionally
