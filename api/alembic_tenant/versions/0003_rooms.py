"""add hotel room tables

Revision ID: 0003_rooms
Revises: 0002_table_state
Create Date: 2025-09-??
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0003_rooms"
down_revision: str | None = "0002_table_state"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table("rooms"):
        op.create_table(
            "rooms",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("code", sa.String, nullable=False, unique=True),
            sa.Column("qr_token", sa.String, nullable=True, unique=True),
            sa.Column("state", sa.Text, nullable=False, server_default="AVAILABLE"),
        )
    if not insp.has_table("room_orders"):
        op.create_table(
            "room_orders",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("room_id", sa.Integer, sa.ForeignKey("rooms.id"), nullable=False),
            sa.Column("status", sa.String, nullable=False),
            sa.Column("placed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("served_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not insp.has_table("room_order_items"):
        op.create_table(
            "room_order_items",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("room_order_id", sa.Integer, sa.ForeignKey("room_orders.id"), nullable=False),
            sa.Column("item_id", sa.Integer, sa.ForeignKey("menu_items.id"), nullable=False),
            sa.Column("name_snapshot", sa.String, nullable=False),
            sa.Column("price_snapshot", sa.Numeric(10,2), nullable=False),
            sa.Column("qty", sa.Integer, nullable=False),
            sa.Column("status", sa.String, nullable=False),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("room_order_items"):
        op.drop_table("room_order_items")
    if insp.has_table("room_orders"):
        op.drop_table("room_orders")
    if insp.has_table("rooms"):
        op.drop_table("rooms")
