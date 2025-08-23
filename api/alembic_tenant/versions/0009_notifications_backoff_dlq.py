"""add attempts and dlq for notifications"""

from alembic import op
import sqlalchemy as sa

revision = "0009_notifications_backoff_dlq"
down_revision = "0008_coupon_stack_cap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notifications_outbox",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "notifications_outbox",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "notifications_dlq",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("original_id", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("error", sa.String(), nullable=False),
        sa.Column(
            "failed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("notifications_dlq")
    op.drop_column("notifications_outbox", "next_attempt_at")
    op.drop_column("notifications_outbox", "attempts")
