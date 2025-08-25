"""hot-path indexes for dashboards/exports

Revision ID: 20250825_0727_hot_indexes
Revises:
Create Date: 2025-08-25
"""

import sqlalchemy as sa
from alembic import op

revision = "20250825_0727_hot_indexes"
down_revision = None
branch_labels = None
depends_on = None

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
