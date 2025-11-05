"""
Email Analytics Service - Phase 3B
Analyse et métriques des emails synchronisés
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from models import db, Agency, Client, ClientInteraction
from collections import defaultdict

logger = logging.getLogger(__name__)


class EmailAnalytics:
    """Service d'analytics pour les emails"""
    
    def __init__(self, agency_id: int):
        self.agency_id = agency_id
        self.agency = Agency.query.get(agency_id)
        
    def get_overview_metrics(self, days: int = 30) -> dict:
        """
        Calcule les métriques principales sur une période donnée.
        
        Args:
            days: Nombre de jours à analyser (7, 30, 90, 365)
            
        Returns:
            dict: Métriques principales
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Total emails synchronisés
            total_emails = ClientInteraction.query.join(Client).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.created_at >= start_date
            ).count()
            
            # Emails reçus (inbound)
            inbound_emails = ClientInteraction.query.join(Client).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.is_outbound == False,
                ClientInteraction.created_at >= start_date
            ).count()
            
            # Emails envoyés (outbound)
            outbound_emails = ClientInteraction.query.join(Client).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.is_outbound == True,
                ClientInteraction.created_at >= start_date
            ).count()
            
            # Taux de réponse
            response_rate = 0
            if inbound_emails > 0:
                response_rate = round((outbound_emails / inbound_emails) * 100, 1)
            
            # Temps de réponse moyen (simplifié - nécessiterait une analyse thread plus complexe)
            avg_response_time_hours = self._calculate_avg_response_time(start_date)
            
            # Clients actifs (avec au moins un email)
            active_clients = db.session.query(func.count(func.distinct(Client.id))).join(
                ClientInteraction
            ).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.created_at >= start_date
            ).scalar()
            
            return {
                'success': True,
                'period_days': days,
                'total_emails': total_emails,
                'inbound_emails': inbound_emails,
                'outbound_emails': outbound_emails,
                'response_rate': response_rate,
                'avg_response_time_hours': avg_response_time_hours,
                'active_clients': active_clients
            }
            
        except Exception as e:
            logger.error(f"Error calculating overview metrics: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_volume_by_day(self, days: int = 30) -> dict:
        """
        Calcule le volume d'emails par jour.
        
        Args:
            days: Nombre de jours à analyser
            
        Returns:
            dict: Volume par jour
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Requête pour obtenir les emails groupés par jour
            results = db.session.query(
                func.date(ClientInteraction.created_at).label('date'),
                func.count(ClientInteraction.id).label('count'),
                func.sum(func.cast(ClientInteraction.is_outbound, db.Integer)).label('outbound'),
                func.sum(func.cast(~ClientInteraction.is_outbound, db.Integer)).label('inbound')
            ).join(Client).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.created_at >= start_date
            ).group_by(
                func.date(ClientInteraction.created_at)
            ).order_by(
                func.date(ClientInteraction.created_at)
            ).all()
            
            # Formater les résultats
            volume_data = []
            for row in results:
                volume_data.append({
                    'date': row.date.strftime('%Y-%m-%d'),
                    'total': row.count,
                    'inbound': row.inbound or 0,
                    'outbound': row.outbound or 0
                })
            
            return {
                'success': True,
                'data': volume_data
            }
            
        except Exception as e:
            logger.error(f"Error calculating volume by day: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_hourly_distribution(self, days: int = 30) -> dict:
        """
        Calcule la distribution horaire des emails.
        
        Args:
            days: Nombre de jours à analyser
            
        Returns:
            dict: Distribution par heure
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Requête pour obtenir les emails groupés par heure
            results = db.session.query(
                func.extract('hour', ClientInteraction.created_at).label('hour'),
                func.count(ClientInteraction.id).label('count')
            ).join(Client).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.created_at >= start_date
            ).group_by(
                func.extract('hour', ClientInteraction.created_at)
            ).order_by(
                func.extract('hour', ClientInteraction.created_at)
            ).all()
            
            # Créer un dict avec toutes les heures (0-23)
            hourly_data = {hour: 0 for hour in range(24)}
            
            for row in results:
                hour = int(row.hour)
                hourly_data[hour] = row.count
            
            # Formater en liste
            distribution = [
                {'hour': hour, 'count': count}
                for hour, count in hourly_data.items()
            ]
            
            return {
                'success': True,
                'data': distribution
            }
            
        except Exception as e:
            logger.error(f"Error calculating hourly distribution: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_top_clients(self, days: int = 30, limit: int = 10) -> dict:
        """
        Retourne les clients avec le plus d'emails.
        
        Args:
            days: Nombre de jours à analyser
            limit: Nombre de clients à retourner
            
        Returns:
            dict: Top clients
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            results = db.session.query(
                Client.id,
                Client.first_name,
                Client.last_name,
                Client.email,
                func.count(ClientInteraction.id).label('email_count')
            ).join(ClientInteraction).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.created_at >= start_date
            ).group_by(
                Client.id, Client.first_name, Client.last_name, Client.email
            ).order_by(
                func.count(ClientInteraction.id).desc()
            ).limit(limit).all()
            
            top_clients = []
            for row in results:
                top_clients.append({
                    'client_id': row.id,
                    'name': f"{row.first_name} {row.last_name}",
                    'email': row.email,
                    'email_count': row.email_count
                })
            
            return {
                'success': True,
                'data': top_clients
            }
            
        except Exception as e:
            logger.error(f"Error getting top clients: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_top_subjects(self, days: int = 30, limit: int = 10) -> dict:
        """
        Retourne les sujets d'emails les plus fréquents.
        
        Args:
            days: Nombre de jours à analyser
            limit: Nombre de sujets à retourner
            
        Returns:
            dict: Top sujets
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            results = db.session.query(
                ClientInteraction.email_subject,
                func.count(ClientInteraction.id).label('count')
            ).join(Client).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.email_subject.isnot(None),
                ClientInteraction.email_subject != '',
                ClientInteraction.created_at >= start_date
            ).group_by(
                ClientInteraction.email_subject
            ).order_by(
                func.count(ClientInteraction.id).desc()
            ).limit(limit).all()
            
            top_subjects = []
            for row in results:
                # Tronquer le sujet si trop long
                subject = row.email_subject
                if len(subject) > 60:
                    subject = subject[:57] + '...'
                
                top_subjects.append({
                    'subject': subject,
                    'count': row.count
                })
            
            return {
                'success': True,
                'data': top_subjects
            }
            
        except Exception as e:
            logger.error(f"Error getting top subjects: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_sentiment_distribution(self, days: int = 30) -> dict:
        """
        Analyse la distribution des sentiments dans les emails.
        Note: Nécessite l'implémentation du sentiment dans ai_summarizer
        
        Args:
            days: Nombre de jours à analyser
            
        Returns:
            dict: Distribution des sentiments
        """
        # Pour l'instant, retourner des données mockées
        # TODO: Implémenter l'analyse de sentiment dans ai_summarizer
        return {
            'success': True,
            'data': [
                {'sentiment': 'positif', 'count': 0, 'percentage': 0},
                {'sentiment': 'neutre', 'count': 0, 'percentage': 0},
                {'sentiment': 'négatif', 'count': 0, 'percentage': 0}
            ],
            'note': 'Sentiment analysis not yet implemented'
        }
    
    def _calculate_avg_response_time(self, start_date: datetime) -> float:
        """
        Calcule le temps de réponse moyen en heures (simplifié).
        
        Args:
            start_date: Date de début de l'analyse
            
        Returns:
            float: Temps moyen en heures
        """
        # Implementation simplifiée - pour une version complète,
        # il faudrait analyser les threads d'emails
        try:
            # Obtenir tous les threads avec emails inbound et outbound
            threads = db.session.query(
                ClientInteraction.email_thread_id
            ).join(Client).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.email_thread_id.isnot(None),
                ClientInteraction.created_at >= start_date
            ).group_by(
                ClientInteraction.email_thread_id
            ).having(
                func.count(ClientInteraction.id) > 1
            ).all()
            
            if not threads:
                return 0
            
            # Pour chaque thread, calculer le temps entre premier inbound et premier outbound
            total_hours = 0
            valid_threads = 0
            
            for (thread_id,) in threads:
                # Premier email reçu
                first_inbound = ClientInteraction.query.join(Client).filter(
                    Client.agency_id == self.agency_id,
                    ClientInteraction.email_thread_id == thread_id,
                    ClientInteraction.is_outbound == False
                ).order_by(ClientInteraction.created_at).first()
                
                # Premier email de réponse
                first_outbound = ClientInteraction.query.join(Client).filter(
                    Client.agency_id == self.agency_id,
                    ClientInteraction.email_thread_id == thread_id,
                    ClientInteraction.is_outbound == True,
                    ClientInteraction.created_at > first_inbound.created_at if first_inbound else datetime.min
                ).order_by(ClientInteraction.created_at).first()
                
                if first_inbound and first_outbound:
                    delta = first_outbound.created_at - first_inbound.created_at
                    hours = delta.total_seconds() / 3600
                    total_hours += hours
                    valid_threads += 1
            
            if valid_threads == 0:
                return 0
            
            return round(total_hours / valid_threads, 1)
            
        except Exception as e:
            logger.error(f"Error calculating avg response time: {str(e)}", exc_info=True)
            return 0
    
    def export_to_csv(self, days: int = 30) -> str:
        """
        Exporte les données analytics en CSV.
        
        Args:
            days: Nombre de jours à exporter
            
        Returns:
            str: Contenu CSV
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Récupérer tous les emails
            emails = db.session.query(
                ClientInteraction.created_at,
                ClientInteraction.email_subject,
                ClientInteraction.email_from,
                ClientInteraction.email_to,
                ClientInteraction.is_outbound,
                Client.first_name,
                Client.last_name
            ).join(Client).filter(
                Client.agency_id == self.agency_id,
                ClientInteraction.interaction_type == 'email',
                ClientInteraction.created_at >= start_date
            ).order_by(ClientInteraction.created_at.desc()).all()
            
            # Créer le CSV
            csv_lines = ['Date,Sujet,De,À,Type,Client\n']
            
            for email in emails:
                date = email.created_at.strftime('%Y-%m-%d %H:%M')
                subject = (email.email_subject or '').replace(',', ';')
                from_addr = (email.email_from or '').replace(',', ';')
                to_addr = (email.email_to or '').replace(',', ';')
                email_type = 'Envoyé' if email.is_outbound else 'Reçu'
                client = f"{email.first_name} {email.last_name}"
                
                csv_lines.append(f'{date},{subject},{from_addr},{to_addr},{email_type},{client}\n')
            
            return ''.join(csv_lines)
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}", exc_info=True)
            return ''
