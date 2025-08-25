"""tenant close restore columns

Revision ID: 20250826_0000_tenant_close_restore
Revises: 20250825_0727_hot_indexes
Create Date: 2025-08-26
"""

import sqlalchemy as sa
from alembic import op

revision = "20250826_0000_tenant_close_restore"
down_revision = "20250825_0727_hot_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tenants") as batch:
        batch.add_column(sa.Column("closed_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("purge_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("tenants") as batch:
        batch.drop_column("closed_at")
        batch.drop_column("purge_at")
