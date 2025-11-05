"""Add email sync Phase 3 fields to Agency

Revision ID: add_email_sync_phase3
Revises: add_email_sync_fields
Create Date: 2025-10-30 15:04:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_email_sync_phase3'
down_revision = 'email_sync_001'
branch_labels = None
depends_on = None


def upgrade():
    # Phase 3A: Auto-sync fields
    op.add_column('agency', sa.Column('auto_sync_enabled', sa.Boolean(), nullable=True))
    op.add_column('agency', sa.Column('sync_frequency', sa.String(length=20), nullable=True))
    op.add_column('agency', sa.Column('last_auto_sync_at', sa.DateTime(), nullable=True))
    op.add_column('agency', sa.Column('auto_sync_errors_count', sa.Integer(), nullable=True))
    
    # Phase 3D: Webhooks fields
    op.add_column('agency', sa.Column('gmail_watch_expiration', sa.DateTime(), nullable=True))
    op.add_column('agency', sa.Column('gmail_history_id', sa.BigInteger(), nullable=True))
    op.add_column('agency', sa.Column('webhook_secret', sa.String(length=255), nullable=True))
    
    # Set default values
    op.execute("UPDATE agency SET auto_sync_enabled = false WHERE auto_sync_enabled IS NULL")
    op.execute("UPDATE agency SET sync_frequency = 'hourly' WHERE sync_frequency IS NULL")
    op.execute("UPDATE agency SET auto_sync_errors_count = 0 WHERE auto_sync_errors_count IS NULL")


def downgrade():
    # Phase 3D: Webhooks fields
    op.drop_column('agency', 'webhook_secret')
    op.drop_column('agency', 'gmail_history_id')
    op.drop_column('agency', 'gmail_watch_expiration')
    
    # Phase 3A: Auto-sync fields
    op.drop_column('agency', 'auto_sync_errors_count')
    op.drop_column('agency', 'last_auto_sync_at')
    op.drop_column('agency', 'sync_frequency')
    op.drop_column('agency', 'auto_sync_enabled')
