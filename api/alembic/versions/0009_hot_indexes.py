"""hot-path indexes for dashboards/exports

Revision ID: 0009_hot_indexes
Revises: 0008_hot_path_indexes
Create Date: 2025-08-25
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0009_hot_indexes"
down_revision: str | None = "0008_hot_path_indexes"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


_STATEMENTS = [
    (
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inv_tenant_created "
        "ON invoices(tenant_id, created_at DESC)"
    ),
    (
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pay_invoice_created "
        "ON payments(invoice_id, created_at DESC)"
    ),
    (
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_tenant_status_created "
        "ON orders(tenant_id, status, created_at DESC)"
    ),
    (
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_tenant_created "
        "ON audit_tenant(tenant_id, created_at DESC)"
    ),
]
_DROP_STATEMENTS = [
    "DROP INDEX IF EXISTS idx_inv_tenant_created",
    "DROP INDEX IF EXISTS idx_pay_invoice_created",
    "DROP INDEX IF EXISTS idx_orders_tenant_status_created",
    "DROP INDEX IF EXISTS idx_audit_tenant_created",
]


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    with op.get_context().autocommit_block():
        for stmt in _STATEMENTS:
            conn.execute(sa.text(stmt))


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    with op.get_context().autocommit_block():
        for stmt in _DROP_STATEMENTS:
            conn.execute(sa.text(stmt))
