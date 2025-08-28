"""add room housekeeping timestamp and nullable order item reference

Revision ID: 0004_rooms
Revises: 0003_rooms, 0003_tables_map_fields
Create Date: 2025-08-21
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0004_rooms"
down_revision: str | tuple[str, ...] | None = ("0003_rooms", "0003_tables_map_fields")
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("rooms"):
        cols = {c["name"] for c in insp.get_columns("rooms")}
        if "last_cleaned_at" not in cols:
            op.add_column(
                "rooms",
                sa.Column("last_cleaned_at", sa.DateTime(timezone=True), nullable=True),
            )
    if insp.has_table("room_orders"):
        cols = {c["name"] for c in insp.get_columns("room_orders")}
        if "placed_at" in cols and conn.dialect.name != "sqlite":
            op.alter_column(
                "room_orders",
                "placed_at",
                existing_type=sa.DateTime(timezone=True),
                nullable=False,
            )
    if insp.has_table("room_order_items"):
        cols = {c["name"] for c in insp.get_columns("room_order_items")}
        if "item_id" in cols and conn.dialect.name != "sqlite":
            op.alter_column(
                "room_order_items",
                "item_id",
                existing_type=sa.Integer(),
                nullable=True,
            )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table("room_order_items"):
        cols = {c["name"] for c in insp.get_columns("room_order_items")}
        if "item_id" in cols and conn.dialect.name != "sqlite":
            op.alter_column(
                "room_order_items",
                "item_id",
                existing_type=sa.Integer(),
                nullable=False,
            )
    if insp.has_table("room_orders"):
        cols = {c["name"] for c in insp.get_columns("room_orders")}
        if "placed_at" in cols and conn.dialect.name != "sqlite":
            op.alter_column(
                "room_orders",
                "placed_at",
                existing_type=sa.DateTime(timezone=True),
                nullable=True,
            )
    if insp.has_table("rooms"):
        cols = {c["name"] for c in insp.get_columns("rooms")}
        if "last_cleaned_at" in cols:
            op.drop_column("rooms", "last_cleaned_at")
