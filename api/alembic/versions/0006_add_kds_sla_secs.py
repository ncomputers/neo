"""add tenant kds sla secs

Revision ID: 0006_add_kds_sla_secs
Revises: 0005_add_tenant_feature_flags
Create Date: 2025-08-27
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0006_add_kds_sla_secs"
down_revision: str | None = "0005_add_tenant_feature_flags"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("kds_sla_secs", sa.Integer(), nullable=False, server_default="900"),
    )


def downgrade() -> None:
    op.drop_column("tenants", "kds_sla_secs")
