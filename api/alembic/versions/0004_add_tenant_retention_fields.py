"""add tenant retention fields

Revision ID: 0004_add_tenant_retention_fields
Revises: 0003_add_tenant_outlet_fields
Create Date: 2025-08-21
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0004_add_tenant_retention_fields"
down_revision: str | None = "0003_add_tenant_outlet_fields"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("retention_days_customers", sa.Integer(), nullable=True))
    op.add_column("tenants", sa.Column("retention_days_outbox", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "retention_days_outbox")
    op.drop_column("tenants", "retention_days_customers")

