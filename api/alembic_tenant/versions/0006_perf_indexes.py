"""add performance indexes"""

"""
Revision ID: 0006_perf_indexes
Revises: 0004_rooms, 0005_counters
Create Date: 2025-08-21
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0006_perf_indexes"
down_revision: tuple[str, str] | None = ("0004_rooms", "0005_counters")
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

INDEXES = [
    ("orders", "ix_orders_status_placed_at", ["status", "placed_at"]),
    ("order_items", "ix_order_items_order_id", ["order_id"]),
    ("invoices", "ix_invoices_created_at", ["created_at"]),
    ("payments", "ix_payments_invoice_id", ["invoice_id"]),
    ("tables", "ix_tables_code", ["code"]),
    ("tables", "ix_tables_qr_token", ["qr_token"]),
    ("room_orders", "ix_room_orders_status_placed_at", ["status", "placed_at"]),
    ("counter_orders", "ix_counter_orders_status_placed_at", ["status", "placed_at"]),
]

def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    for table, name, cols in INDEXES:
        if insp.has_table(table):
            index_names = {ix["name"] for ix in insp.get_indexes(table)}
            if name not in index_names:
                op.create_index(name, table, cols)

def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    for table, name, cols in INDEXES:
        if insp.has_table(table):
            index_names = {ix["name"] for ix in insp.get_indexes(table)}
            if name in index_names:
                op.drop_index(name, table_name=table)
