"""add tenant outlet fields

Revision ID: 0003_add_tenant_outlet_fields
Revises: 0002_add_sync_outbox_table
Create Date: 2024-08-18
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0003_add_tenant_outlet_fields"
down_revision: str | None = "0002_add_sync_outbox_table"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("timezone", sa.String(), nullable=True))
    op.add_column(
        "tenants",
        sa.Column(
            "licensed_tables", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "tenants",
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
    )


def downgrade() -> None:
    op.drop_column("tenants", "status")
    op.drop_column("tenants", "licensed_tables")
    op.drop_column("tenants", "timezone")

