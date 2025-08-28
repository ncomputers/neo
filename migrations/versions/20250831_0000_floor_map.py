"""floor map tables and geometry

Revision ID: 20250831_0000_floor_map
Revises: 20250830_0000_audit_log_partitions
Create Date: 2025-08-31
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "20250831_0000_floor_map"
down_revision = "20250830_0000_audit_log_partitions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tables") as batch:
        batch.alter_column(
            "pos_x", existing_type=sa.Integer(), nullable=True, server_default=None
        )
        batch.alter_column(
            "pos_y", existing_type=sa.Integer(), nullable=True, server_default=None
        )
        batch.alter_column(
            "label", existing_type=sa.Text(), type_=sa.String(length=32), nullable=True
        )
        batch.add_column(
            sa.Column("width", sa.Integer(), nullable=True, server_default="80")
        )
        batch.add_column(
            sa.Column("height", sa.Integer(), nullable=True, server_default="80")
        )
        batch.add_column(
            sa.Column(
                "shape", sa.String(length=12), nullable=True, server_default="rect"
            )
        )
        batch.add_column(sa.Column("zone", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("capacity", sa.Integer(), nullable=True))

    op.create_table(
        "floor_maps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("viewport_w", sa.Integer(), nullable=True),
        sa.Column("viewport_h", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("floor_maps")
    with op.batch_alter_table("tables") as batch:
        batch.drop_column("capacity")
        batch.drop_column("zone")
        batch.drop_column("shape")
        batch.drop_column("height")
        batch.drop_column("width")
        batch.alter_column(
            "label", existing_type=sa.String(length=32), type_=sa.Text(), nullable=True
        )
        batch.alter_column(
            "pos_y", existing_type=sa.Integer(), nullable=False, server_default="0"
        )
        batch.alter_column(
            "pos_x", existing_type=sa.Integer(), nullable=False, server_default="0"
        )
