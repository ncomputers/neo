"""add coupon caps, windows, and usage audit"""

"""
Revision ID: 0013_coupon_caps_windows
Revises: 0012_soft_delete_and_unique_indexes
Create Date: 2025-09-25
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0013_coupon_caps_windows"
down_revision: str | None = "0012_soft_delete_and_unique_indexes"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column("coupons", sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True))
    op.add_column("coupons", sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True))
    op.add_column("coupons", sa.Column("per_day_cap", sa.Integer(), nullable=True))
    op.add_column("coupons", sa.Column("per_guest_cap", sa.Integer(), nullable=True))
    op.add_column("coupons", sa.Column("per_outlet_cap", sa.Integer(), nullable=True))

    op.create_table(
        "coupon_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("coupon_id", sa.Integer(), sa.ForeignKey("coupons.id"), nullable=False),
        sa.Column("guest_id", sa.Integer(), nullable=True),
        sa.Column("outlet_id", sa.Integer(), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("coupon_usage")
    op.drop_column("coupons", "per_outlet_cap")
    op.drop_column("coupons", "per_guest_cap")
    op.drop_column("coupons", "per_day_cap")
    op.drop_column("coupons", "valid_to")
    op.drop_column("coupons", "valid_from")
