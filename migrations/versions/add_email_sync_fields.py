"""add email sync fields

Revision ID: email_sync_001
Revises: 1106985f0c5b
Create Date: 2025-10-30 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'email_sync_001'
down_revision = '1106985f0c5b'
branch_labels = None
depends_on = None


def upgrade():
    # Extension du modèle Agency pour Email Sync
    op.add_column('agency', sa.Column('email_sync_enabled', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('agency', sa.Column('email_provider', sa.String(length=20), nullable=True))
    op.add_column('agency', sa.Column('email_access_token_encrypted', sa.Text(), nullable=True))
    op.add_column('agency', sa.Column('email_refresh_token_encrypted', sa.Text(), nullable=True))
    op.add_column('agency', sa.Column('email_token_expiry', sa.DateTime(), nullable=True))
    op.add_column('agency', sa.Column('email_sync_address', sa.String(length=255), nullable=True))
    op.add_column('agency', sa.Column('last_email_sync', sa.DateTime(), nullable=True))
    op.add_column('agency', sa.Column('email_sync_history_id', sa.String(length=100), nullable=True))
    
    # Extension du modèle ClientInteraction pour les emails
    op.add_column('client_interactions', sa.Column('email_message_id', sa.String(length=255), nullable=True))
    op.add_column('client_interactions', sa.Column('email_thread_id', sa.String(length=255), nullable=True))
    op.add_column('client_interactions', sa.Column('email_subject', sa.String(length=500), nullable=True))
    op.add_column('client_interactions', sa.Column('email_from', sa.String(length=255), nullable=True))
    op.add_column('client_interactions', sa.Column('email_to', sa.String(length=255), nullable=True))
    op.add_column('client_interactions', sa.Column('email_cc', sa.Text(), nullable=True))
    op.add_column('client_interactions', sa.Column('is_outbound', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('client_interactions', sa.Column('ai_summary', sa.Text(), nullable=True))
    
    # Créer des index pour les recherches fréquentes
    op.create_index('ix_client_interactions_email_message_id', 'client_interactions', ['email_message_id'])
    op.create_index('ix_client_interactions_email_thread_id', 'client_interactions', ['email_thread_id'])
    op.create_index('ix_agency_email_sync_enabled', 'agency', ['email_sync_enabled'])


def downgrade():
    # Supprimer les index
    op.drop_index('ix_agency_email_sync_enabled', table_name='agency')
    op.drop_index('ix_client_interactions_email_thread_id', table_name='client_interactions')
    op.drop_index('ix_client_interactions_email_message_id', table_name='client_interactions')
    
    # Supprimer les colonnes de ClientInteraction
    op.drop_column('client_interactions', 'ai_summary')
    op.drop_column('client_interactions', 'is_outbound')
    op.drop_column('client_interactions', 'email_cc')
    op.drop_column('client_interactions', 'email_to')
    op.drop_column('client_interactions', 'email_from')
    op.drop_column('client_interactions', 'email_subject')
    op.drop_column('client_interactions', 'email_thread_id')
    op.drop_column('client_interactions', 'email_message_id')
    
    # Supprimer les colonnes de Agency
    op.drop_column('agency', 'email_sync_history_id')
    op.drop_column('agency', 'last_email_sync')
    op.drop_column('agency', 'email_sync_address')
    op.drop_column('agency', 'email_token_expiry')
    op.drop_column('agency', 'email_refresh_token_encrypted')
    op.drop_column('agency', 'email_access_token_encrypted')
    op.drop_column('agency', 'email_provider')
    op.drop_column('agency', 'email_sync_enabled')
