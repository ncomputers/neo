"""add room housekeeping timestamp and nullable order item reference

Revision ID: 0004_rooms
Revises: 0003_rooms, 0003_tables_map_fields
Create Date: 2025-08-21
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0004_rooms"
down_revision: str | tuple[str, ...] | None = ("0003_rooms", "0003_tables_map_fields")
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("rooms") and not insp.has_column("rooms", "last_cleaned_at"):
        op.add_column(
            "rooms",
            sa.Column("last_cleaned_at", sa.DateTime(timezone=True), nullable=True),
        )
    if insp.has_table("room_orders") and insp.has_column("room_orders", "placed_at"):
        op.alter_column(
            "room_orders",
            "placed_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
        )
    if insp.has_table("room_order_items") and insp.has_column("room_order_items", "item_id"):
        op.alter_column(
            "room_order_items",
            "item_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("room_order_items") and insp.has_column("room_order_items", "item_id"):
        op.alter_column(
            "room_order_items",
            "item_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
    if insp.has_table("room_orders") and insp.has_column("room_orders", "placed_at"):
        op.alter_column(
            "room_orders",
            "placed_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
        )
    if insp.has_table("rooms") and insp.has_column("rooms", "last_cleaned_at"):
        op.drop_column("rooms", "last_cleaned_at")
