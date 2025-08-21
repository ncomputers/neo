"""add table map position fields

Revision ID: 0003_tables_map_fields
Revises: 0002_table_state
Create Date: 2024-10-07
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0003_tables_map_fields"
down_revision: str | None = "0002_table_state"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_column("tables", "pos_x"):
        op.add_column(
            "tables",
            sa.Column("pos_x", sa.Integer(), nullable=False, server_default="0"),
        )
    if not insp.has_column("tables", "pos_y"):
        op.add_column(
            "tables",
            sa.Column("pos_y", sa.Integer(), nullable=False, server_default="0"),
        )
    if not insp.has_column("tables", "label"):
        op.add_column(
            "tables",
            sa.Column("label", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_column("tables", "label"):
        op.drop_column("tables", "label")
    if insp.has_column("tables", "pos_y"):
        op.drop_column("tables", "pos_y")
    if insp.has_column("tables", "pos_x"):
        op.drop_column("tables", "pos_x")
