"""
Gestionnaire principal de synchronisation email
Orchestre la synchronisation, le matching et le stockage des emails
"""

from models import db, Agency, Client, ClientInteraction, User
from .gmail_sync import GmailSyncService
from .outlook_sync import OutlookSync
from .email_parser import EmailParser, EmailMatcher
from .ai_summarizer import EmailSummarizer
from utils.crypto import decrypt_api_key
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


class EmailSyncManager:
    """Gestionnaire principal pour la synchronisation email"""
    
    def __init__(self, agency):
        """
        Initialise le gestionnaire de synchronisation
        
        Args:
            agency: Instance du modèle Agency
        """
        self.agency = agency
        self.sync_service = None
        self.summarizer = EmailSummarizer(agency=agency)
        
        # Vérifier que la sync est activée
        if not agency.email_sync_enabled:
            raise ValueError("La synchronisation email n'est pas activée pour cette agence")
        
        # Initialiser le service de sync selon le provider
        self._init_sync_service()
    
    def _init_sync_service(self):
        """Initialise le service de synchronisation selon le provider"""
        try:
            provider = self.agency.email_sync_provider or self.agency.email_provider
            
            if provider == 'gmail':
                # Déchiffrer les tokens
                access_token = decrypt_api_key(self.agency.email_access_token_encrypted)
                refresh_token = decrypt_api_key(self.agency.email_refresh_token_encrypted) if self.agency.email_refresh_token_encrypted else None
                
                self.sync_service = GmailSyncService(access_token, refresh_token)
                logger.info(f"Service Gmail initialisé pour {self.agency.name}")
                
            elif provider == 'outlook':
                # Récupérer les credentials Outlook depuis l'environnement
                outlook_client_id = os.getenv('OUTLOOK_CLIENT_ID')
                outlook_client_secret = os.getenv('OUTLOOK_CLIENT_SECRET')
                outlook_tenant_id = os.getenv('OUTLOOK_TENANT_ID', 'common')
                
                if not outlook_client_id or not outlook_client_secret:
                    raise ValueError("Les credentials Outlook ne sont pas configurés dans .env")
                
                self.sync_service = OutlookSync(
                    self.agency,
                    outlook_client_id,
                    outlook_client_secret,
                    outlook_tenant_id
                )
                logger.info(f"Service Outlook initialisé pour {self.agency.name}")
                
            elif provider == 'manual':
                # Configuration SMTP/IMAP manuelle
                from .imap_sync import IMAPSyncService
                from utils.crypto import decrypt_config
                
                # Déchiffrer la config IMAP
                if not self.agency.imap_config_encrypted:
                    raise ValueError("Configuration IMAP manquante")
                
                imap_config = decrypt_config(self.agency.imap_config_encrypted)
                
                self.sync_service = IMAPSyncService(imap_config)
                logger.info(f"Service IMAP manuel initialisé pour {self.agency.name}")
            else:
                raise ValueError(f"Provider non supporté: {provider}")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du service de sync: {e}")
            raise
    
    def sync_emails(self, max_emails=50):
        """
        Synchronise les nouveaux emails
        
        Args:
            max_emails: Nombre maximum d'emails à synchroniser
            
        Returns:
            Dict avec les statistiques de synchronisation
        """
        logger.info(f"Début de synchronisation pour {self.agency.name}")
        
        stats = {
            'total_fetched': 0,
            'processed': 0,
            'matched': 0,
            'saved': 0,
            'skipped': 0,
            'errors': 0
        }
        
        try:
            # Récupérer les nouveaux messages
            history_id = self.agency.email_sync_history_id
            message_ids = self.sync_service.get_new_messages(
                history_id=history_id,
                max_results=max_emails
            )
            
            stats['total_fetched'] = len(message_ids)
            
            # Traiter chaque message
            for message_id in message_ids:
                try:
                    self._process_email(message_id, stats)
                    stats['processed'] += 1
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de {message_id}: {e}")
                    stats['errors'] += 1
            
            # Mettre à jour l'historique
            new_history_id = self.sync_service.get_current_history_id()
            if new_history_id:
                self.agency.email_sync_history_id = new_history_id
            
            self.agency.last_email_sync = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Synchronisation terminée: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation: {e}")
            db.session.rollback()
            raise
    
    def _process_email(self, message_id, stats):
        """
        Traite un email individuel
        
        Args:
            message_id: ID du message
            stats: Dict de statistiques à mettre à jour
        """
        # Vérifier si l'email existe déjà
        existing = ClientInteraction.query.filter_by(
            email_message_id=message_id
        ).first()
        
        if existing:
            logger.debug(f"Email {message_id} déjà synchronisé, skip")
            stats['skipped'] += 1
            return
        
        # Récupérer les détails de l'email
        email_data = self.sync_service.get_message_details(message_id)
        
        # Vérifier si l'email est pertinent (implique l'agence)
        if not EmailMatcher.is_relevant_email(email_data, self.agency.email_sync_address):
            logger.debug(f"Email {message_id} non pertinent, skip")
            stats['skipped'] += 1
            return
        
        # Chercher le client concerné
        client = EmailMatcher.determine_client_from_email(
            email_data,
            self.agency.id,
            self.agency.email_sync_address
        )
        
        if not client:
            logger.debug(f"Aucun client trouvé pour {message_id}, skip")
            stats['skipped'] += 1
            return
        
        stats['matched'] += 1
        
        # Nettoyer le corps de l'email
        cleaned_body = EmailParser.clean_email_body(email_data['body'])
        
        # Générer un résumé IA
        ai_summary = self.summarizer.summarize_email(
            email_data['subject'],
            cleaned_body
        )
        
        # Déterminer l'utilisateur (créer une interaction au nom du premier admin si email entrant)
        user = None
        if email_data.get('is_sent'):
            # Pour les emails envoyés, essayer de trouver l'utilisateur via l'email
            # Pour l'instant, utiliser le premier admin
            user = User.query.filter_by(
                agency_id=self.agency.id,
                role='agency_admin'
            ).first()
        else:
            # Pour les emails reçus, utiliser le premier admin aussi
            user = User.query.filter_by(
                agency_id=self.agency.id,
                role='agency_admin'
            ).first()
        
        if not user:
            # Fallback: premier utilisateur de l'agence
            user = User.query.filter_by(agency_id=self.agency.id).first()
        
        if not user:
            logger.error(f"Aucun utilisateur trouvé pour créer l'interaction")
            stats['errors'] += 1
            return
        
        # Créer l'interaction
        interaction = ClientInteraction(
            client_id=client.id,
            user_id=user.id,
            interaction_type='email',
            content=cleaned_body,
            email_message_id=message_id,
            email_thread_id=email_data['thread_id'],
            email_subject=email_data['subject'],
            email_from=email_data['from'],
            email_to=email_data['to'],
            email_cc=email_data.get('cc', ''),
            is_outbound=email_data.get('is_sent', False),
            ai_summary=ai_summary,
            created_at=email_data['date']
        )
        
        db.session.add(interaction)
        db.session.commit()
        
        # Envoyer une notification temps réel si l'email est entrant
        if not email_data.get('is_sent', False):
            try:
                from services.notification_service import NotificationService
                NotificationService.notify_new_email(
                    agency_id=self.agency.id,
                    interaction_id=interaction.id
                )
                logger.debug(f"Notification envoyée pour l'email {message_id}")
            except Exception as e:
                # Ne pas bloquer la sync si la notification échoue
                logger.warning(f"Erreur lors de l'envoi de la notification: {e}")
        
        stats['saved'] += 1
        logger.info(f"Email {message_id} sauvegardé pour client {client.id}")
    
    def test_connection(self):
        """
        Teste la connexion au service email
        
        Returns:
            True si OK, False sinon
        """
        try:
            if self.sync_service:
                return self.sync_service.test_connection()
            return False
        except Exception as e:
            logger.error(f"Erreur lors du test de connexion: {e}")
            return False
    
    def get_sync_status(self):
        """
        Récupère le statut de la synchronisation
        
        Returns:
            Dict avec les informations de statut
        """
        return {
            'enabled': self.agency.email_sync_enabled,
            'provider': self.agency.email_provider,
            'email': self.agency.email_sync_address,
            'last_sync': self.agency.last_email_sync.isoformat() if self.agency.last_email_sync else None,
            'connection_ok': self.test_connection()
        }
    
    @staticmethod
    def disable_sync(agency):
        """
        Désactive la synchronisation pour une agence
        
        Args:
            agency: Instance du modèle Agency
        """
        agency.email_sync_enabled = False
        agency.email_provider = None
        agency.email_access_token_encrypted = None
        agency.email_refresh_token_encrypted = None
        agency.email_token_expiry = None
        agency.email_sync_address = None
        agency.email_sync_history_id = None
        
        db.session.commit()
        logger.info(f"Synchronisation désactivée pour {agency.name}")
