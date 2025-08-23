"""Add retry columns and DLQ for notifications"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = '0009_notifications_retry_dlq'
down_revision = '0008_coupon_stack_cap'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'notifications_outbox',
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'notifications_outbox',
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        'notifications_dlq',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('original_id', sa.Integer(), nullable=False),
        sa.Column('event', sa.String(), nullable=False),
        sa.Column('channel', sa.String(), nullable=False),
        sa.Column('target', sa.String(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('error', sa.String(), nullable=False),
        sa.Column('failed_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('notifications_dlq')
    op.drop_column('notifications_outbox', 'next_attempt_at')
    op.drop_column('notifications_outbox', 'attempts')
