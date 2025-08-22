"""add stackable and cap to coupons

Revision ID: 0008_coupon_stack_cap
Revises: 0007_invoice_tip
Create Date: 2025-09-17
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0008_coupon_stack_cap"
down_revision: str | None = "0007_invoice_tip"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "coupons",
        sa.Column(
            "is_stackable", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "coupons",
        sa.Column("max_discount", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("coupons", "max_discount")
    op.drop_column("coupons", "is_stackable")
