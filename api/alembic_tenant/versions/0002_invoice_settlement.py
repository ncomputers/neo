"""add invoice settled columns

Revision ID: 0002_invoice_settlement
Revises: 0001_initial_tenant
Create Date: 2024-06-09
"""

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

revision: str = "0002_invoice_settlement"
down_revision: str | None = "0001_initial_tenant"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("settled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "invoices",
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invoices", "settled_at")
    op.drop_column("invoices", "settled")
