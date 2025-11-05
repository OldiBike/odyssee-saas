"""
services/email_sync - Module de synchronisation email pour le CRM

Ce module gère :
- L'authentification OAuth2 (Gmail et Outlook)
- La synchronisation des emails
- Le matching des emails avec les clients
- Les résumés IA des emails
"""

from .gmail_sync import GmailSyncService
from .email_parser import EmailParser, EmailMatcher
from .ai_summarizer import EmailSummarizer
from .email_sync_manager import EmailSyncManager

# OutlookSyncService sera importé quand implémenté
# from .outlook_sync import OutlookSyncService

__all__ = [
    'GmailSyncService',
    'EmailParser',
    'EmailMatcher',
    'EmailSummarizer',
    'EmailSyncManager'
]
