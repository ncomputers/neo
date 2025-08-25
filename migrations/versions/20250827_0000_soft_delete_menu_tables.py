"""soft delete columns for menu items and tables

Revision ID: 20250827_0000_soft_delete_menu_tables
Revises: 20250826_0000_tenant_close_restore
Create Date: 2025-08-27
"""

import sqlalchemy as sa
from alembic import op

revision = "20250827_0000_soft_delete_menu_tables"
down_revision = "20250826_0000_tenant_close_restore"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("menu_items") as batch:
        batch.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
    with op.batch_alter_table("tables") as batch:
        batch.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("menu_items") as batch:
        batch.drop_column("deleted_at")
    with op.batch_alter_table("tables") as batch:
        batch.drop_column("deleted_at")
