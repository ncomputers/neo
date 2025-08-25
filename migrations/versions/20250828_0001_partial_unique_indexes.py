"""partial unique indexes for tables and menu items

Revision ID: 20250828_0001_partial_unique_indexes
Revises: 20250827_0000_soft_delete_menu_tables
Create Date: 2025-08-28
"""

import sqlalchemy as sa
from alembic import op

revision = "20250828_0001_partial_unique_indexes"
down_revision = "20250827_0000_soft_delete_menu_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    with op.get_context().autocommit_block():
        conn.execute(sa.text("DROP INDEX IF EXISTS tables_code_key"))
        conn.execute(
            sa.text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_tables_tenant_code_active "
                "ON tables(tenant_id, code) WHERE deleted_at IS NULL"
            )
        )
        conn.execute(
            sa.text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_menu_items_tenant_sku_active "
                "ON menu_items(tenant_id, sku) WHERE deleted_at IS NULL"
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    with op.get_context().autocommit_block():
        conn.execute(sa.text("DROP INDEX IF EXISTS idx_tables_tenant_code_active"))
        conn.execute(sa.text("DROP INDEX IF EXISTS idx_menu_items_tenant_sku_active"))
        conn.execute(
            sa.text("ALTER TABLE tables ADD CONSTRAINT tables_code_key UNIQUE (code)")
        )
