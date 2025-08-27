"""hot-path indexes for tenant queries

Revision ID: 0008_hot_path_indexes
Revises: 0007_rename_invoice_columns
Create Date: 2025-02-14
"""

from alembic import op
from sqlalchemy import inspect

revision: str = "0008_hot_path_indexes"
down_revision: str | None = "0007_rename_invoice_columns"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("invoices"):
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_inv_tenant_created "
            "ON invoices (tenant_id, created_at DESC)"
        )
    if inspector.has_table("payments"):
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_pay_invoice_created "
            "ON payments (invoice_id, created_at DESC)"
        )
    if inspector.has_table("orders"):
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_orders_tenant_status_created "
            "ON orders (tenant_id, status, created_at DESC)"
        )
    if inspector.has_table("audit_tenant"):
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_tenant_created "
            "ON audit_tenant (tenant_id, created_at DESC)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("invoices"):
        indexes = {i["name"] for i in inspector.get_indexes("invoices")}
        if "idx_inv_tenant_created" in indexes:
            op.execute("DROP INDEX IF EXISTS idx_inv_tenant_created")
    if inspector.has_table("payments"):
        indexes = {i["name"] for i in inspector.get_indexes("payments")}
        if "idx_pay_invoice_created" in indexes:
            op.execute("DROP INDEX IF EXISTS idx_pay_invoice_created")
    if inspector.has_table("orders"):
        indexes = {i["name"] for i in inspector.get_indexes("orders")}
        if "idx_orders_tenant_status_created" in indexes:
            op.execute("DROP INDEX IF EXISTS idx_orders_tenant_status_created")
    if inspector.has_table("audit_tenant"):
        indexes = {i["name"] for i in inspector.get_indexes("audit_tenant")}
        if "idx_audit_tenant_created" in indexes:
            op.execute("DROP INDEX IF EXISTS idx_audit_tenant_created")
