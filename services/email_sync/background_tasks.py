"""
Background Tasks for Email Synchronization
Phase 3A: Synchronisation Automatique
"""
import logging
from datetime import datetime
from models import db, Agency, ClientInteraction, Client
from services.email_sync.email_sync_manager import EmailSyncManager

logger = logging.getLogger(__name__)

# Instance globale de socketio (sera initialisée par l'app)
_socketio = None


def set_socketio(socketio_instance):
    """Configure l'instance SocketIO pour les notifications"""
    global _socketio
    _socketio = socketio_instance
    logger.info("SocketIO instance configured for background tasks")


def sync_agency_emails(agency_id: int) -> dict:
    """
    Synchronise les emails d'une agence spécifique.
    
    Args:
        agency_id: ID de l'agence à synchroniser
        
    Returns:
        dict: Résultats de la synchronisation
    """
    try:
        agency = Agency.query.get(agency_id)
        if not agency:
            logger.error(f"Agency {agency_id} not found")
            return {
                'success': False,
                'error': 'Agency not found',
                'agency_id': agency_id
            }
        
        # Vérifier si la sync est activée
        if not agency.email_sync_enabled:
            logger.info(f"Email sync disabled for agency {agency_id}")
            return {
                'success': False,
                'error': 'Email sync disabled',
                'agency_id': agency_id
            }
        
        logger.info(f"Starting automatic email sync for agency {agency_id} ({agency.name})")
        
        # Créer le manager et synchroniser
        manager = EmailSyncManager(agency_id)
        result = manager.sync_emails()
        
        # Mettre à jour les stats de sync auto
        agency.last_auto_sync_at = datetime.utcnow()
        
        if result.get('success'):
            # Reset error count on success
            agency.auto_sync_errors_count = 0
            new_emails_count = result.get('new_emails', 0)
            logger.info(f"Successfully synced {new_emails_count} new emails for agency {agency_id}")
            
            # Émettre des notifications SocketIO pour les nouveaux emails
            if new_emails_count > 0 and _socketio:
                notify_new_emails(agency_id, result.get('stats', {}))
        else:
            # Increment error count
            agency.auto_sync_errors_count = (agency.auto_sync_errors_count or 0) + 1
            logger.error(f"Error syncing emails for agency {agency_id}: {result.get('error')}")
        
        db.session.commit()
        
        return result
        
    except Exception as e:
        logger.error(f"Exception in sync_agency_emails for agency {agency_id}: {str(e)}", exc_info=True)
        
        # Increment error count
        try:
            agency = Agency.query.get(agency_id)
            if agency:
                agency.auto_sync_errors_count = (agency.auto_sync_errors_count or 0) + 1
                db.session.commit()
        except:
            pass
        
        return {
            'success': False,
            'error': str(e),
            'agency_id': agency_id
        }


def sync_all_agencies() -> dict:
    """
    Synchronise les emails de toutes les agences ayant la sync auto activée.
    
    Returns:
        dict: Résultats globaux de la synchronisation
    """
    logger.info("Starting automatic email sync for all agencies")
    
    try:
        # Récupérer toutes les agences avec auto-sync activée
        agencies = Agency.query.filter_by(
            email_sync_enabled=True,
            auto_sync_enabled=True
        ).all()
        
        if not agencies:
            logger.info("No agencies with auto-sync enabled")
            return {
                'success': True,
                'agencies_count': 0,
                'synced': 0,
                'failed': 0,
                'results': []
            }
        
        logger.info(f"Found {len(agencies)} agencies with auto-sync enabled")
        
        results = []
        synced_count = 0
        failed_count = 0
        
        for agency in agencies:
            result = sync_agency_emails(agency.id)
            results.append({
                'agency_id': agency.id,
                'agency_name': agency.name,
                'success': result.get('success', False),
                'new_emails': result.get('new_emails', 0),
                'error': result.get('error')
            })
            
            if result.get('success'):
                synced_count += 1
            else:
                failed_count += 1
        
        logger.info(f"Sync completed: {synced_count} successful, {failed_count} failed")
        
        return {
            'success': True,
            'agencies_count': len(agencies),
            'synced': synced_count,
            'failed': failed_count,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Exception in sync_all_agencies: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'agencies_count': 0,
            'synced': 0,
            'failed': 0
        }


def notify_new_emails(agency_id: int, stats: dict):
    """
    Émet des événements SocketIO pour notifier les utilisateurs de nouveaux emails.
    
    Args:
        agency_id: ID de l'agence
        stats: Statistiques de synchronisation
    """
    global _socketio
    
    if not _socketio:
        logger.warning("SocketIO not configured, skipping notifications")
        return
    
    try:
        # Récupérer les emails non lus récents (dernières 5 minutes)
        from datetime import timedelta
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        
        recent_emails = db.session.query(ClientInteraction).join(Client).filter(
            Client.agency_id == agency_id,
            ClientInteraction.interaction_type == 'email',
            ClientInteraction.is_outbound == False,
            ClientInteraction.is_read == False,
            ClientInteraction.created_at >= five_minutes_ago
        ).order_by(ClientInteraction.created_at.desc()).limit(10).all()
        
        if not recent_emails:
            logger.debug(f"No new unread emails to notify for agency {agency_id}")
            return
        
        # Émettre un événement pour chaque nouvel email
        room = f'agency_{agency_id}'
        
        for email in recent_emails:
            client = email.client
            email_data = {
                'id': email.id,
                'client_id': client.id if client else None,
                'client_name': f"{client.first_name} {client.last_name}" if client else 'Client inconnu',
                'subject': email.email_subject or 'Sans sujet',
                'received_at': email.created_at.isoformat() if email.created_at else None,
                'has_summary': bool(email.ai_summary)
            }
            
            _socketio.emit('new_email', email_data, room=room)
            logger.info(f"Emitted notification for email {email.id} to room {room}")
        
        # Mettre à jour le compteur global
        total_unread = db.session.query(ClientInteraction).join(Client).filter(
            Client.agency_id == agency_id,
            ClientInteraction.interaction_type == 'email',
            ClientInteraction.is_outbound == False,
            ClientInteraction.is_read == False
        ).count()
        
        _socketio.emit('unread_count', {'count': total_unread}, room=room)
        logger.info(f"Updated unread count to {total_unread} for agency {agency_id}")
        
    except Exception as e:
        logger.error(f"Error in notify_new_emails for agency {agency_id}: {str(e)}", exc_info=True)


def check_and_notify_errors():
    """
    Vérifie les agences avec trop d'erreurs de sync et notifie les admins.
    Cette fonction peut être appelée périodiquement.
    """
    try:
        # Trouver les agences avec plus de 5 erreurs consécutives
        agencies_with_errors = Agency.query.filter(
            Agency.auto_sync_enabled == True,
            Agency.auto_sync_errors_count > 5
        ).all()
        
        if agencies_with_errors:
            logger.warning(f"Found {len(agencies_with_errors)} agencies with repeated sync errors")
            
            for agency in agencies_with_errors:
                logger.warning(
                    f"Agency {agency.id} ({agency.name}) has {agency.auto_sync_errors_count} "
                    f"consecutive sync errors. Last sync: {agency.last_auto_sync_at}"
                )
                
                # TODO: Implémenter notification par email aux admins de l'agence
                # Cela pourrait utiliser le système Flask-Mail existant
        
    except Exception as e:
        logger.error(f"Exception in check_and_notify_errors: {str(e)}", exc_info=True)
