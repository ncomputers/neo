"""add tip column to invoices

Revision ID: 0007_invoice_tip
Revises: 0006_perf_indexes
Create Date: 2025-09-16
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0007_invoice_tip"
down_revision: str | None = "0006_perf_indexes"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("tip", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("invoices", "tip")
