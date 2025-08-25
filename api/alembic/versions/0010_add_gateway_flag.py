"""add tenant gateway flag

Revision ID: 0010_add_gateway_flag
Revises: 0009_hot_indexes
Create Date: 2025-09-02
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0010_add_gateway_flag"
down_revision: str | None = "0009_hot_indexes"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("enable_gateway", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("tenants", "enable_gateway")
