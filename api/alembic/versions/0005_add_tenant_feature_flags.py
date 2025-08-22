"""add tenant feature flags

Revision ID: 0005_add_tenant_feature_flags
Revises: 0004_add_tenant_retention_fields
Create Date: 2025-08-27
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0005_add_tenant_feature_flags"
down_revision: str | None = "0004_add_tenant_retention_fields"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("enable_hotel", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "tenants",
        sa.Column("enable_counter", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("tenants", "enable_counter")
    op.drop_column("tenants", "enable_hotel")

