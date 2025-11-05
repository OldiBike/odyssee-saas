"""Add notification tracking fields to client_interactions

Revision ID: add_notification_fields
Revises: add_smtp_imap_config
Create Date: 2025-10-31 08:37:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_notification_fields'
down_revision = 'add_smtp_imap_config'
branch_labels = None
depends_on = None


def upgrade():
    # Ajouter les champs de tracking de lecture
    op.add_column('client_interactions', 
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('client_interactions', 
        sa.Column('read_at', sa.DateTime(), nullable=True))
    op.add_column('client_interactions', 
        sa.Column('read_by_user_id', sa.Integer(), nullable=True))


def downgrade():
    # Supprimer les champs
    op.drop_column('client_interactions', 'read_by_user_id')
    op.drop_column('client_interactions', 'read_at')
    op.drop_column('client_interactions', 'is_read')
