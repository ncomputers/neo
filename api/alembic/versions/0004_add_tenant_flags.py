"""add tenant flags column

Revision ID: 0004_add_tenant_flags
Revises: 0003_add_tenant_outlet_fields
Create Date: 2024-08-18
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0004_add_tenant_flags"
down_revision: str | None = "0003_add_tenant_outlet_fields"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("flags", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "flags")
