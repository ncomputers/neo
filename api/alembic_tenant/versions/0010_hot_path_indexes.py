"""add hot-path indexes and optional partitions"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_hot_path_indexes"
down_revision = "0009_notifications_backoff_dlq"
branch_labels = None
depends_on = None

INDEXES = [
    ("invoices", "ix_invoices_created_at", ["created_at"]),
    ("payments", "ix_payments_invoice_id_created_at", ["invoice_id", "created_at"]),
    ("orders", "ix_orders_status_created_at", ["status", "created_at"]),
    ("orders", "ix_orders_status_placed_at", ["status", "placed_at"]),
    ("order_items", "ix_order_items_order_id", ["order_id"]),
    ("audit_tenant", "ix_audit_tenant_at", ["at"]),
]


def _ensure_monthly_partition(conn: sa.engine.Connection, table: str) -> None:
    """Ensure the current month's partition exists for a table.

    Only runs on PostgreSQL and when the parent table is partitioned by
    ``created_at``.
    """
    if conn.dialect.name != "postgresql":
        return
    is_partitioned = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_partitioned_table p
            JOIN pg_class c ON c.oid = p.partrelid
            WHERE c.relname = :table
            """
        ),
        {"table": table},
    ).scalar()
    if not is_partitioned:
        return
    conn.execute(
        sa.text(
            """
            DO $$
            DECLARE
                start_month date := date_trunc('month', CURRENT_DATE);
                end_month   date := start_month + INTERVAL '1 month';
                part_name   text :=
                    format('%I_%s', :table, to_char(start_month, 'YYYYMM'));
            BEGIN
                EXECUTE format(
                    'CREATE TABLE IF NOT EXISTS %s PARTITION OF %s '
                    'FOR VALUES FROM (%L) TO (%L)',
                    part_name,
                    :table,
                    start_month,
                    end_month,
                );
            END$$;
            """
        ),
        {"table": table},
    )


def upgrade() -> None:  # pragma: no cover - covered via tests
    conn = op.get_bind()
    insp = sa.inspect(conn)
    for table, name, cols in INDEXES:
        if not insp.has_table(table):
            continue
        if not all(insp.has_column(table, c) for c in cols):
            continue
        index_names = {ix["name"] for ix in insp.get_indexes(table)}
        if name not in index_names:
            op.create_index(name, table, cols)
    for table in ("invoices", "payments"):
        _ensure_monthly_partition(conn, table)


def downgrade() -> None:  # pragma: no cover - symmetry with upgrade
    conn = op.get_bind()
    insp = sa.inspect(conn)
    for table, name, _ in INDEXES:
        if not insp.has_table(table):
            continue
        index_names = {ix["name"] for ix in insp.get_indexes(table)}
        if name in index_names:
            op.drop_index(name, table_name=table)
