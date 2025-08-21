"""add takeaway counter entities

Revision ID: 0005_counters
Revises: 0003_tables_map_fields
Create Date: 2025-02-15
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0005_counters"
down_revision: str | None = "0003_tables_map_fields"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("counters"):
        op.create_table(
            "counters",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("code", sa.String, nullable=False, unique=True),
            sa.Column("qr_token", sa.String, nullable=True, unique=True),
        )
    if not insp.has_table("counter_orders"):
        op.create_table(
            "counter_orders",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("counter_id", sa.Integer, sa.ForeignKey("counters.id"), nullable=False),
            sa.Column("status", sa.Text, nullable=False),
            sa.Column("placed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not insp.has_table("counter_order_items"):
        op.create_table(
            "counter_order_items",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("counter_order_id", sa.Integer, sa.ForeignKey("counter_orders.id"), nullable=False),
            sa.Column("item_id", sa.Integer, sa.ForeignKey("menu_items.id"), nullable=True),
            sa.Column("name_snapshot", sa.Text, nullable=False),
            sa.Column("price_snapshot", sa.Numeric(10, 2), nullable=False),
            sa.Column("qty", sa.Integer, nullable=False),
            sa.Column("status", sa.Text, nullable=False),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("counter_order_items"):
        op.drop_table("counter_order_items")
    if insp.has_table("counter_orders"):
        op.drop_table("counter_orders")
    if insp.has_table("counters"):
        op.drop_table("counters")
