"""customer consent flags

Revision ID: 20250829_0000_customer_consent_flags
Revises: 20250828_0001_partial_unique_indexes
Create Date: 2025-08-29
"""

import sqlalchemy as sa
from alembic import op

revision = "20250829_0000_customer_consent_flags"
down_revision = "20250828_0001_partial_unique_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("customers") as batch:
        batch.add_column(sa.Column("allow_analytics", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("allow_wa", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("customers") as batch:
        batch.drop_column("allow_analytics")
        batch.drop_column("allow_wa")
