"""
Email Search Service - Phase 3F
Recherche et filtres avancés pour les emails
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import or_, and_, func
from models import db, Agency, Client, ClientInteraction

logger = logging.getLogger(__name__)


class EmailSearch:
    """Service de recherche avancée pour les emails"""
    
    def __init__(self, agency_id: int):
        self.agency_id = agency_id
    
    def search(self, 
               query: Optional[str] = None,
               sender: Optional[str] = None,
               recipient: Optional[str] = None,
               client_id: Optional[int] = None,
               date_from: Optional[datetime] = None,
               date_to: Optional[datetime] = None,
               is_outbound: Optional[bool] = None,
               has_attachments: Optional[bool] = None,
               limit: int = 100,
               offset: int = 0) -> Dict:
        """
        Recherche des emails avec filtres avancés.
        
        Args:
            query: Recherche textuelle dans sujet et contenu
            sender: Filtre par expéditeur
            recipient: Filtre par destinataire
            client_id: Filtre par client
            date_from: Date de début
            date_to: Date de fin
            is_outbound: Filtre type (True=envoyé, False=reçu, None=tous)
            has_attachments: Emails avec pièces jointes
            limit: Nombre max de résultats
            offset: Décalage pour pagination
            
        Returns:
            dict: Résultats de la recherche
        """
        try:
            # Construire la requête de base
            base_query = ClientInteraction.query.join(Client).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email'
            )
            
            # Appliquer les filtres
            
            # Recherche textuelle
            if query:
                search_pattern = f'%{query}%'
                base_query = base_query.filter(
                    or_(
                        ClientInteraction.email_subject.ilike(search_pattern),
                        ClientInteraction.content.ilike(search_pattern),
                        ClientInteraction.ai_summary.ilike(search_pattern)
                    )
                )
            
            # Filtre expéditeur
            if sender:
                sender_pattern = f'%{sender}%'
                base_query = base_query.filter(
                    ClientInteraction.email_from.ilike(sender_pattern)
                )
            
            # Filtre destinataire
            if recipient:
                recipient_pattern = f'%{recipient}%'
                base_query = base_query.filter(
                    or_(
                        ClientInteraction.email_to.ilike(recipient_pattern),
                        ClientInteraction.email_cc.ilike(recipient_pattern)
                    )
                )
            
            # Filtre client
            if client_id:
                base_query = base_query.filter(
                    ClientInteraction.client_id == client_id
                )
            
            # Filtre date de début
            if date_from:
                base_query = base_query.filter(
                    ClientInteraction.created_at >= date_from
                )
            
            # Filtre date de fin
            if date_to:
                # Ajouter 1 jour pour inclure toute la journée
                date_to_end = date_to + timedelta(days=1)
                base_query = base_query.filter(
                    ClientInteraction.created_at < date_to_end
                )
            
            # Filtre type (envoyé/reçu)
            if is_outbound is not None:
                base_query = base_query.filter(
                    ClientInteraction.is_outbound == is_outbound
                )
            
            # Compter le total de résultats
            total_count = base_query.count()
            
            # Appliquer pagination et récupérer les résultats
            results = base_query.order_by(
                ClientInteraction.created_at.desc()
            ).limit(limit).offset(offset).all()
            
            # Formater les résultats
            emails = []
            for interaction in results:
                email_data = {
                    'id': interaction.id,
                    'client_id': interaction.client_id,
                    'client_name': f"{interaction.client.first_name} {interaction.client.last_name}",
                    'email_from': interaction.email_from,
                    'email_to': interaction.email_to,
                    'email_cc': interaction.email_cc,
                    'subject': interaction.email_subject,
                    'snippet': interaction.content[:200] if interaction.content else '',
                    'ai_summary': interaction.ai_summary,
                    'is_outbound': interaction.is_outbound,
                    'created_at': interaction.created_at.strftime('%Y-%m-%d %H:%M'),
                    'thread_id': interaction.email_thread_id
                }
                emails.append(email_data)
            
            return {
                'success': True,
                'total': total_count,
                'count': len(emails),
                'limit': limit,
                'offset': offset,
                'emails': emails
            }
            
        except Exception as e:
            logger.error(f"Error searching emails: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'total': 0,
                'emails': []
            }
    
    def get_thread(self, thread_id: str) -> Dict:
        """
        Récupère tous les emails d'un thread.
        
        Args:
            thread_id: ID du thread
            
        Returns:
            dict: Emails du thread
        """
        try:
            emails = ClientInteraction.query.join(Client).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.email_thread_id == thread_id
            ).order_by(ClientInteraction.created_at).all()
            
            thread_emails = []
            for interaction in emails:
                email_data = {
                    'id': interaction.id,
                    'client_id': interaction.client_id,
                    'client_name': f"{interaction.client.first_name} {interaction.client.last_name}",
                    'email_from': interaction.email_from,
                    'email_to': interaction.email_to,
                    'email_cc': interaction.email_cc,
                    'subject': interaction.email_subject,
                    'content': interaction.content,
                    'ai_summary': interaction.ai_summary,
                    'is_outbound': interaction.is_outbound,
                    'created_at': interaction.created_at.strftime('%Y-%m-%d %H:%M')
                }
                thread_emails.append(email_data)
            
            return {
                'success': True,
                'thread_id': thread_id,
                'count': len(thread_emails),
                'emails': thread_emails
            }
            
        except Exception as e:
            logger.error(f"Error getting thread: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'emails': []
            }
    
    def get_client_emails(self, client_id: int, limit: int = 50) -> Dict:
        """
        Récupère tous les emails d'un client spécifique.
        
        Args:
            client_id: ID du client
            limit: Nombre max d'emails
            
        Returns:
            dict: Emails du client
        """
        try:
            # Vérifier que le client appartient à l'agence
            client = Client.query.filter_by(
                id=client_id,
                agency_id=self.agency_id
            ).first()
            
            if not client:
                return {
                    'success': False,
                    'error': 'Client not found',
                    'emails': []
                }
            
            emails = ClientInteraction.query.filter_by(
                client_id=client_id,
                interaction_type='email'
            ).order_by(
                ClientInteraction.created_at.desc()
            ).limit(limit).all()
            
            email_list = []
            for interaction in emails:
                email_data = {
                    'id': interaction.id,
                    'email_from': interaction.email_from,
                    'email_to': interaction.email_to,
                    'subject': interaction.email_subject,
                    'snippet': interaction.content[:200] if interaction.content else '',
                    'ai_summary': interaction.ai_summary,
                    'is_outbound': interaction.is_outbound,
                    'created_at': interaction.created_at.strftime('%Y-%m-%d %H:%M'),
                    'thread_id': interaction.email_thread_id
                }
                email_list.append(email_data)
            
            return {
                'success': True,
                'client_id': client_id,
                'client_name': f"{client.first_name} {client.last_name}",
                'count': len(email_list),
                'emails': email_list
            }
            
        except Exception as e:
            logger.error(f"Error getting client emails: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'emails': []
            }
    
    def get_unread_emails(self, limit: int = 50) -> Dict:
        """
        Récupère les emails non lus (marquage à implémenter).
        
        Args:
            limit: Nombre max d'emails
            
        Returns:
            dict: Emails non lus
        """
        # Pour l'instant, retourner les emails récents reçus (inbound)
        try:
            recent_date = datetime.utcnow() - timedelta(days=7)
            
            emails = ClientInteraction.query.join(Client).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.is_outbound == False,
                ClientInteraction.created_at >= recent_date
            ).order_by(
                ClientInteraction.created_at.desc()
            ).limit(limit).all()
            
            email_list = []
            for interaction in emails:
                email_data = {
                    'id': interaction.id,
                    'client_id': interaction.client_id,
                    'client_name': f"{interaction.client.first_name} {interaction.client.last_name}",
                    'email_from': interaction.email_from,
                    'subject': interaction.email_subject,
                    'snippet': interaction.content[:200] if interaction.content else '',
                    'ai_summary': interaction.ai_summary,
                    'created_at': interaction.created_at.strftime('%Y-%m-%d %H:%M')
                }
                email_list.append(email_data)
            
            return {
                'success': True,
                'count': len(email_list),
                'emails': email_list
            }
            
        except Exception as e:
            logger.error(f"Error getting unread emails: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'emails': []
            }
    
    def get_suggested_filters(self) -> Dict:
        """
        Retourne des suggestions de filtres basées sur les données existantes.
        
        Returns:
            dict: Suggestions de filtres
        """
        try:
            # Top expéditeurs
            top_senders = db.session.query(
                ClientInteraction.email_from,
                func.count(ClientInteraction.id).label('count')
            ).join(Client).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.email_from.isnot(None),
                ClientInteraction.email_from != ''
            ).group_by(
                ClientInteraction.email_from
            ).order_by(
                func.count(ClientInteraction.id).desc()
            ).limit(10).all()
            
            # Top sujets (mots-clés)
            top_subjects = db.session.query(
                ClientInteraction.email_subject,
                func.count(ClientInteraction.id).label('count')
            ).join(Client).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.email_subject.isnot(None),
                ClientInteraction.email_subject != ''
            ).group_by(
                ClientInteraction.email_subject
            ).order_by(
                func.count(ClientInteraction.id).desc()
            ).limit(10).all()
            
            return {
                'success': True,
                'top_senders': [
                    {'email': sender, 'count': count}
                    for sender, count in top_senders
                ],
                'top_subjects': [
                    {'subject': subject[:50], 'count': count}
                    for subject, count in top_subjects
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting suggested filters: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'top_senders': [],
                'top_subjects': []
            }
