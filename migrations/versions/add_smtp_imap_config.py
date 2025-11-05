"""Add SMTP/IMAP manual config fields

Revision ID: add_smtp_imap_config
Revises: add_email_sync_phase3_fields
Create Date: 2025-10-30 16:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_smtp_imap_config'
down_revision = 'add_email_sync_phase3'
branch_labels = None
depends_on = None


def upgrade():
    # Ajouter les champs de configuration SMTP/IMAP manuelle
    op.add_column('agency', sa.Column('smtp_config_encrypted', sa.Text(), nullable=True))
    op.add_column('agency', sa.Column('imap_config_encrypted', sa.Text(), nullable=True))
    op.add_column('agency', sa.Column('email_config_type', sa.String(length=20), nullable=True))  # 'oauth' ou 'manual'
    op.add_column('agency', sa.Column('email_sync_provider', sa.String(length=50), nullable=True))  # 'gmail', 'outlook', 'manual'
    op.add_column('agency', sa.Column('email_sync_email', sa.String(length=255), nullable=True))  # Adresse email pour sync manuel
    op.add_column('agency', sa.Column('email_last_sync_at', sa.DateTime(), nullable=True))  # Dernière synchronisation


def downgrade():
    op.drop_column('agency', 'email_last_sync_at')
    op.drop_column('agency', 'email_sync_email')
    op.drop_column('agency', 'email_sync_provider')
    op.drop_column('agency', 'email_config_type')
    op.drop_column('agency', 'imap_config_encrypted')
    op.drop_column('agency', 'smtp_config_encrypted')
