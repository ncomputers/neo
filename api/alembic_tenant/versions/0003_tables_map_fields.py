"""add table map position fields

Revision ID: 0003_tables_map_fields
Revises: 0002_table_state
Create Date: 2024-10-07
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0003_tables_map_fields"
down_revision: str | None = "0002_table_state"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("tables")}
    if "pos_x" not in cols:
        op.add_column(
            "tables",
            sa.Column("pos_x", sa.Integer(), nullable=True, server_default="0"),
        )
    if "pos_y" not in cols:
        op.add_column(
            "tables",
            sa.Column("pos_y", sa.Integer(), nullable=True, server_default="0"),
        )
    if "label" not in cols:
        op.add_column(
            "tables",
            sa.Column("label", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("tables")}
    if "label" in cols:
        op.drop_column("tables", "label")
    if "pos_y" in cols:
        op.drop_column("tables", "pos_y")
    if "pos_x" in cols:
        op.drop_column("tables", "pos_x")
