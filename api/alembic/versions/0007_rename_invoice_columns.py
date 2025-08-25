"""rename invoice columns

Revision ID: 0007_rename_invoice_columns
Revises: 0006_add_kds_sla_secs
Create Date: 2024-07-20
"""

from alembic import op

revision: str = "0007_rename_invoice_columns"
down_revision: str | None = "0006_add_kds_sla_secs"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.alter_column("tenants", "invoice_prefix", new_column_name="inv_prefix")
    op.alter_column("tenants", "invoice_reset", new_column_name="inv_reset")


def downgrade() -> None:
    op.alter_column("tenants", "inv_prefix", new_column_name="invoice_prefix")
    op.alter_column("tenants", "inv_reset", new_column_name="invoice_reset")
