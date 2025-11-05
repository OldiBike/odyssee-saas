"""
Service de notifications en temps réel
Gère l'envoi et la réception de notifications via SocketIO
"""
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Gère l'envoi de notifications en temps réel"""
    
    @staticmethod
    def notify_new_email(agency_id: int, interaction_id: int):
        """
        Envoie une notification pour un nouvel email
        
        Args:
            agency_id: ID de l'agence
            interaction_id: ID de l'interaction email
        """
        from app import socketio
        from models import ClientInteraction, Client
        
        try:
            # Récupérer les détails de l'email
            interaction = ClientInteraction.query.get(interaction_id)
            if not interaction:
                logger.warning(f"Interaction {interaction_id} non trouvée")
                return
            
            client = Client.query.get(interaction.client_id)
            if not client:
                logger.warning(f"Client {interaction.client_id} non trouvé")
                return
            
            # Préparer le payload de notification
            notification_data = {
                'id': interaction.id,
                'client_id': client.id,
                'client_name': f"{client.first_name} {client.last_name}",
                'client_email': client.email,
                'subject': interaction.email_subject or 'Sans sujet',
                'summary': interaction.ai_summary or (interaction.content[:100] if interaction.content else ''),
                'received_at': interaction.created_at.isoformat() if interaction.created_at else datetime.utcnow().isoformat(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Émettre vers tous les utilisateurs de l'agence
            room = f'agency_{agency_id}'
            socketio.emit('new_email', notification_data, room=room)
            
            logger.info(f"Notification envoyée pour l'email {interaction_id} à l'agence {agency_id}")
            
        except Exception as e:
            logger.error(f"Erreur envoi notification: {e}", exc_info=True)
    
    @staticmethod
    def get_unread_count(agency_id: int, user_id: int = None) -> int:
        """
        Compte les emails non lus pour une agence
        
        Args:
            agency_id: ID de l'agence
            user_id: ID de l'utilisateur (non utilisé pour le moment, pour évolution future)
            
        Returns:
            int: Nombre d'emails non lus
        """
        from models import db, ClientInteraction, Client
        
        try:
            # Compter les interactions email non lues
            count = db.session.query(ClientInteraction).join(Client).filter(
                Client.agency_id == agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.is_outbound == False,
                ClientInteraction.is_read == False
            ).count()
            
            return count
        except Exception as e:
            logger.error(f"Erreur get_unread_count: {e}", exc_info=True)
            return 0
    
    @staticmethod
    def get_recent_unread_emails(agency_id: int, limit: int = 5):
        """
        Récupère les emails non lus récents
        
        Args:
            agency_id: ID de l'agence
            limit: Nombre d'emails à récupérer
            
        Returns:
            list: Liste d'emails non lus
        """
        from models import db, ClientInteraction, Client
        
        try:
            interactions = db.session.query(ClientInteraction).join(Client).filter(
                Client.agency_id == agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.is_outbound == False,
                ClientInteraction.is_read == False
            ).order_by(ClientInteraction.created_at.desc()).limit(limit).all()
            
            result = []
            for interaction in interactions:
                client = Client.query.get(interaction.client_id)
                if client:
                    result.append({
                        'id': interaction.id,
                        'client_id': client.id,
                        'client_name': f"{client.first_name} {client.last_name}",
                        'client_email': client.email,
                        'subject': interaction.email_subject or 'Sans sujet',
                        'summary': interaction.ai_summary or (interaction.content[:100] if interaction.content else ''),
                        'received_at': interaction.created_at.isoformat() if interaction.created_at else datetime.utcnow().isoformat()
                    })
            
            return result
        except Exception as e:
            logger.error(f"Erreur get_recent_unread_emails: {e}", exc_info=True)
            return []
    
    @staticmethod
    def mark_as_read(interaction_id: int, user_id: int = None) -> bool:
        """
        Marque un email comme lu
        
        Args:
            interaction_id: ID de l'interaction
            user_id: ID de l'utilisateur qui marque comme lu (optionnel)
            
        Returns:
            bool: True si succès
        """
        from models import db, ClientInteraction
        
        try:
            interaction = ClientInteraction.query.get(interaction_id)
            if not interaction:
                logger.warning(f"Interaction {interaction_id} non trouvée")
                return False
            
            interaction.is_read = True
            interaction.read_at = datetime.utcnow()
            if user_id:
                interaction.read_by_user_id = user_id
            
            db.session.commit()
            logger.info(f"Email {interaction_id} marqué comme lu")
            return True
            
        except Exception as e:
            logger.error(f"Erreur mark_as_read: {e}", exc_info=True)
            db.session.rollback()
            return False
    
    @staticmethod
    def mark_all_as_read(agency_id: int, user_id: int = None) -> int:
        """
        Marque tous les emails non lus d'une agence comme lus
        
        Args:
            agency_id: ID de l'agence
            user_id: ID de l'utilisateur qui marque comme lu (optionnel)
            
        Returns:
            int: Nombre d'emails marqués comme lus
        """
        from models import db, ClientInteraction, Client
        
        try:
            # Récupérer tous les emails non lus
            interactions = db.session.query(ClientInteraction).join(Client).filter(
                Client.agency_id == agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.is_outbound == False,
                ClientInteraction.is_read == False
            ).all()
            
            count = 0
            for interaction in interactions:
                interaction.is_read = True
                interaction.read_at = datetime.utcnow()
                if user_id:
                    interaction.read_by_user_id = user_id
                count += 1
            
            db.session.commit()
            logger.info(f"{count} emails marqués comme lus pour l'agence {agency_id}")
            return count
            
        except Exception as e:
            logger.error(f"Erreur mark_all_as_read: {e}", exc_info=True)
            db.session.rollback()
            return 0
