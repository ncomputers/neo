"""hot-path indexes for dashboards/exports

Revision ID: 0009_hot_indexes
Revises: 0008_hot_path_indexes
Create Date: 2025-08-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0009_hot_indexes"
down_revision: str | None = "0008_hot_path_indexes"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


# Mapping of tables to their index creation SQL.
_INDEX_QUERIES: dict[str, str] = {
    "invoices": (
        "CREATE INDEX CONCURRENTLY idx_inv_tenant_created "
        "ON invoices(tenant_id, created_at DESC)"
    ),
    "payments": (
        "CREATE INDEX CONCURRENTLY idx_pay_invoice_created "
        "ON payments(invoice_id, created_at DESC)"
    ),
    "orders": (
        "CREATE INDEX CONCURRENTLY idx_orders_tenant_status_created "
        "ON orders(tenant_id, status, created_at DESC)"
    ),
    "audit_tenant": (
        "CREATE INDEX CONCURRENTLY idx_audit_tenant_created "
        "ON audit_tenant(tenant_id, created_at DESC)"
    ),
}


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    inspector = inspect(conn)
    with op.get_context().autocommit_block():
        for table, stmt in _INDEX_QUERIES.items():
            if inspector.has_table(table):
                existing = {i["name"] for i in inspector.get_indexes(table)}
                name = stmt.split()[4]
                if name not in existing:
                    conn.execute(sa.text(stmt))


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    inspector = inspect(conn)
    with op.get_context().autocommit_block():
        for table, stmt in _INDEX_QUERIES.items():
            if inspector.has_table(table):
                name = stmt.split()[4]
                existing = {i["name"] for i in inspector.get_indexes(table)}
                if name in existing:
                    conn.execute(sa.text(f"DROP INDEX IF EXISTS {name}"))
