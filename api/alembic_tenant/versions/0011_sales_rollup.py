"""create sales_rollup table

Revision ID: 0011_sales_rollup
Revises: 0010_hot_path_indexes, 0010_hot_indexes_partitions
Create Date: 2024-05-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "0011_sales_rollup"
down_revision: tuple[str, ...] | None = (
    "0010_hot_path_indexes",
    "0010_hot_indexes_partitions",
)
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "sales_rollup",
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("d", sa.Date(), nullable=False),
        sa.Column("orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sales", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("tax", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("tip", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("modes_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("tenant_id", "d"),
    )


def downgrade() -> None:
    op.drop_table("sales_rollup")
