"""add deleted_at and partial unique indexes"""

"""
Revision ID: 0012_soft_delete_unique_indexes
Revises: 0011_sales_rollup
Create Date: 2025-09-20
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0012_soft_delete_unique_indexes"
down_revision: str | None = "0011_sales_rollup"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "deleted_at" not in {c["name"] for c in insp.get_columns("menu_items")}:
        op.add_column(
            "menu_items",
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "deleted_at" not in {c["name"] for c in insp.get_columns("tables")}:
        op.add_column(
            "tables", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
        )
    if conn.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            cols = {c["name"] for c in insp.get_columns("tables")}
            if {"tenant_id", "code"}.issubset(cols):
                conn.execute(
                    sa.text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS idx_tables_tenant_code_active "
                        "ON tables(tenant_id, code) WHERE deleted_at IS NULL"
                    )
                )
            cols = {c["name"] for c in insp.get_columns("menu_items")}
            if {"tenant_id", "sku"}.issubset(cols):
                conn.execute(
                    sa.text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS idx_menu_items_tenant_sku_active "
                        "ON menu_items(tenant_id, sku) WHERE deleted_at IS NULL"
                    )
                )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            conn.execute(sa.text("DROP INDEX IF EXISTS idx_tables_tenant_code_active"))
            conn.execute(
                sa.text("DROP INDEX IF EXISTS idx_menu_items_tenant_sku_active")
            )
    for table in ("tables", "menu_items"):
        insp = sa.inspect(conn)
        if "deleted_at" in {c["name"] for c in insp.get_columns(table)}:
            op.drop_column(table, "deleted_at")
