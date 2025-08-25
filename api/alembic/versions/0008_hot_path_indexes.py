"""hot-path indexes for tenant queries

Revision ID: 0008_hot_path_indexes
Revises: 0007_rename_invoice_columns
Create Date: 2025-02-14
"""

from alembic import op

revision: str = "0008_hot_path_indexes"
down_revision: str | None = "0007_rename_invoice_columns"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_invoices_tenant_created "
        "ON invoices (tenant_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_payments_invoice_created "
        "ON payments (invoice_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_tenant_status_created "
        "ON orders (tenant_id, status, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_tenant_created "
        "ON audit_tenant (tenant_id, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_invoices_tenant_created")
    op.execute("DROP INDEX IF EXISTS idx_payments_invoice_created")
    op.execute("DROP INDEX IF EXISTS idx_orders_tenant_status_created")
    op.execute("DROP INDEX IF EXISTS idx_audit_tenant_created")
