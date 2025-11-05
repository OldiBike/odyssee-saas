"""
services/analytics.py - Service d'analyse de données et métriques CRM
Gère les statistiques de vente, performances des vendeurs, et analytics client.
"""

from models import db, Trip, Client, User, SalesReport, ClientInteraction
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
import json


class AnalyticsService:
    """Service central pour toutes les analyses et métriques"""
    
    @staticmethod
    def get_agency_dashboard_metrics(agency_id: int, period_days: int = 30) -> Dict:
        """
        Récupère les métriques principales pour le dashboard agence
        
        Args:
            agency_id: ID de l'agence
            period_days: Période d'analyse en jours (défaut: 30)
            
        Returns:
            Dict contenant toutes les métriques
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Voyages du période
        trips = Trip.query.filter(
            Trip.agency_id == agency_id,
            Trip.created_at >= start_date
        ).all()
        
        # Voyages vendus
        sold_trips = [t for t in trips if t.status == 'sold']
        
        # Calcul du CA
        total_revenue = sum(t.price for t in sold_trips)
        
        # Panier moyen
        average_sale = total_revenue // len(sold_trips) if sold_trips else 0
        
        # Taux de conversion
        conversion_rate = (len(sold_trips) / len(trips) * 100) if trips else 0
        
        # Nouveaux clients
        new_clients = Client.query.filter(
            Client.agency_id == agency_id,
            Client.created_at >= start_date
        ).count()
        
        return {
            'period_days': period_days,
            'total_trips': len(trips),
            'sold_trips': len(sold_trips),
            'proposed_trips': len([t for t in trips if t.status == 'proposed']),
            'total_revenue': total_revenue,
            'average_sale': average_sale,
            'conversion_rate': round(conversion_rate, 2),
            'new_clients': new_clients,
            'top_destinations': AnalyticsService._get_top_destinations(sold_trips, limit=5)
        }
    
    @staticmethod
    def get_seller_performance(user_id: int, period_days: int = 30) -> Dict:
        """
        Analyse complète des performances d'un vendeur pour la page de détail
        
        Args:
            user_id: ID du vendeur
            period_days: Période d'analyse (défaut: 30 jours / mois en cours)
            
        Returns:
            Dict avec toutes les métriques du vendeur
        """
        user = User.query.get(user_id)
        if not user:
            return {}
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Voyages du vendeur sur la période
        trips = Trip.query.filter(
            Trip.user_id == user_id,
            Trip.created_at >= start_date
        ).all()
        
        sold_trips = [t for t in trips if t.status == 'sold']
        proposed_trips = [t for t in trips if t.status == 'proposed']
        assigned_trips = [t for t in trips if t.status == 'assigned']
        
        # CA du mois
        monthly_revenue = sum(t.price for t in sold_trips)
        monthly_sales = len(sold_trips)
        
        # Objectif mensuel & complétion
        objective_completion = 0
        if user.sales_target and user.sales_target > 0:
            objective_completion = int((monthly_revenue / user.sales_target) * 100)
        
        # Commissions totales
        total_commissions = 0
        if user.commission_rate:
            total_commissions = (monthly_revenue * user.commission_rate) // 100
        
        # Taux de conversion
        conversion_rate = round((monthly_sales / len(trips) * 100), 2) if trips else 0
        
        # Panier moyen
        average_sale = monthly_revenue // monthly_sales if monthly_sales > 0 else 0
        
        # Taux de closing (assignés → vendus)
        closing_rate = round((monthly_sales / (monthly_sales + len(assigned_trips)) * 100), 2) if (monthly_sales + len(assigned_trips)) > 0 else 0
        
        # Séjours vs excursions
        sejours_count = sum(1 for t in sold_trips if not t.is_day_trip)
        day_trips_count = sum(1 for t in sold_trips if t.is_day_trip)
        
        # Top destinations
        dest_stats = {}
        for trip in sold_trips:
            dest = trip.destination
            if dest not in dest_stats:
                dest_stats[dest] = {'destination': dest, 'count': 0, 'revenue': 0}
            dest_stats[dest]['count'] += 1
            dest_stats[dest]['revenue'] += trip.price
        
        top_destinations = sorted(dest_stats.values(), key=lambda x: x['count'], reverse=True)[:5]
        
        # Tendance mensuelle (6 derniers mois)
        monthly_trend = AnalyticsService._get_seller_monthly_trend(user_id, 6)
        
        # Croissance par rapport au mois précédent
        sales_growth = 0
        if len(monthly_trend['revenue']) >= 2:
            current = monthly_trend['revenue'][-1]
            previous = monthly_trend['revenue'][-2]
            if previous > 0:
                sales_growth = round(((current - previous) / previous) * 100, 2)
        
        # Total all-time
        all_sold_trips = Trip.query.filter_by(user_id=user_id, status='sold').all()
        total_revenue_alltime = sum(t.price for t in all_sold_trips)
        total_sales_alltime = len(all_sold_trips)
        
        return {
            'user_id': user_id,
            'pseudo': user.pseudo,
            'monthly_revenue': monthly_revenue,
            'monthly_sales': monthly_sales,
            'objective_completion': objective_completion,
            'sales_growth': sales_growth,
            'conversion_rate': conversion_rate,
            'proposed_trips': len(proposed_trips),
            'assigned_trips': len(assigned_trips),
            'total_commissions': total_commissions,
            'average_sale': average_sale,
            'closing_rate': closing_rate,
            'sejours_count': sejours_count,
            'day_trips_count': day_trips_count,
            'top_destinations': top_destinations,
            'monthly_trend': monthly_trend,
            'total_revenue': total_revenue_alltime,
            'total_sales': total_sales_alltime
        }
    
    @staticmethod
    def _get_seller_monthly_trend(user_id: int, months: int = 6) -> Dict:
        """
        Tendance mensuelle pour un vendeur spécifique
        
        Args:
            user_id: ID du vendeur
            months: Nombre de mois à analyser
            
        Returns:
            Dict avec données mensuelles
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 31)
        
        trips = Trip.query.filter(
            Trip.user_id == user_id,
            Trip.status == 'sold',
            Trip.sold_at >= start_date
        ).all()
        
        # Agrégation par mois
        monthly_data = {}
        for trip in trips:
            if not trip.sold_at:
                continue
            
            month_key = trip.sold_at.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {'month': month_key, 'sales': 0, 'revenue': 0}
            monthly_data[month_key]['sales'] += 1
            monthly_data[month_key]['revenue'] += trip.price
        
        # Trier chronologiquement
        sorted_data = sorted(monthly_data.values(), key=lambda x: x['month'])
        
        return {
            'months': [d['month'] for d in sorted_data],
            'sales': [d['sales'] for d in sorted_data],
            'revenue': [d['revenue'] for d in sorted_data]
        }
    
    @staticmethod
    def get_client_insights(client_id: int) -> Dict:
        """
        Analyse approfondie d'un client (profil CRM)
        
        Args:
            client_id: ID du client
            
        Returns:
            Dict avec insights client
        """
        client = Client.query.get(client_id)
        if not client:
            return {}
        
        # Historique des voyages
        trips = Trip.query.filter_by(client_id=client_id).all()
        sold_trips = [t for t in trips if t.status == 'sold']
        
        # Interactions
        interactions = ClientInteraction.query.filter_by(
            client_id=client_id
        ).order_by(ClientInteraction.created_at.desc()).limit(10).all()
        
        # Destinations préférées
        destinations = {}
        for trip in sold_trips:
            dest = trip.destination
            destinations[dest] = destinations.get(dest, 0) + 1
        
        top_destinations = sorted(destinations.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Ancienneté
        days_since_first_trip = 0
        if sold_trips:
            first_trip_date = min(t.sold_at for t in sold_trips if t.sold_at)
            days_since_first_trip = (datetime.now() - first_trip_date).days
        
        return {
            'client_id': client_id,
            'full_name': f"{client.first_name} {client.last_name}",
            'client_type': client.client_type or 'nouveau',
            'total_trips': len(sold_trips),
            'total_spent': client.total_revenue or 0,
            'average_trip_value': (client.total_revenue // len(sold_trips)) if sold_trips else 0,
            'last_purchase': client.last_purchase_date.strftime('%d/%m/%Y') if client.last_purchase_date else None,
            'days_since_first_trip': days_since_first_trip,
            'top_destinations': [{'destination': d[0], 'count': d[1]} for d in top_destinations],
            'recent_interactions': [i.to_dict() for i in interactions],
            'preferences': client.preferences or {}
        }
    
    @staticmethod
    def get_team_leaderboard(agency_id: int, period_days: int = 30) -> List[Dict]:
        """
        Classement des vendeurs par performance avec détails complets
        
        Args:
            agency_id: ID de l'agence
            period_days: Période d'analyse (défaut: 30 jours)
            
        Returns:
            Liste des vendeurs classés par CA avec métriques détaillées
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Tous les vendeurs de l'agence (incluant agency_admin)
        sellers = User.query.filter_by(
            agency_id=agency_id,
            is_active=True
        ).filter(User.role.in_(['agency_admin', 'seller'])).all()
        
        leaderboard = []
        for seller in sellers:
            # Voyages du vendeur sur la période
            trips = Trip.query.filter(
                Trip.user_id == seller.id,
                Trip.created_at >= start_date
            ).all()
            
            sold_trips = [t for t in trips if t.status == 'sold']
            
            # Métriques
            revenue = sum(t.price for t in sold_trips)
            sales = len(sold_trips)
            conversion_rate = round((sales / len(trips) * 100), 2) if trips else 0
            
            # Commission
            commission = 0
            if seller.commission_rate and revenue > 0:
                commission = (revenue * seller.commission_rate) // 100
            
            leaderboard.append({
                'seller': seller,  # Objet User complet
                'sales': sales,
                'revenue': revenue,
                'conversion_rate': conversion_rate,
                'commission': commission
            })
        
        # Tri par CA décroissant
        leaderboard.sort(key=lambda x: x['revenue'], reverse=True)
        
        return leaderboard
    
    @staticmethod
    def get_destinations_analytics(agency_id: int, period_days: int = 90) -> List[Dict]:
        """
        Analyse des destinations les plus vendues
        
        Args:
            agency_id: ID de l'agence
            period_days: Période d'analyse
            
        Returns:
            Liste des destinations avec statistiques
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        trips = Trip.query.filter(
            Trip.agency_id == agency_id,
            Trip.status == 'sold',
            Trip.sold_at >= start_date
        ).all()
        
        # Agrégation par destination
        dest_stats = {}
        for trip in trips:
            dest = trip.destination
            if dest not in dest_stats:
                dest_stats[dest] = {
                    'destination': dest,
                    'trips_count': 0,
                    'total_revenue': 0,
                    'average_price': 0,
                    'prices': []
                }
            dest_stats[dest]['trips_count'] += 1
            dest_stats[dest]['total_revenue'] += trip.price
            dest_stats[dest]['prices'].append(trip.price)
        
        # Calcul des moyennes
        results = []
        for dest, stats in dest_stats.items():
            stats['average_price'] = stats['total_revenue'] // stats['trips_count']
            stats['min_price'] = min(stats['prices'])
            stats['max_price'] = max(stats['prices'])
            del stats['prices']  # Nettoyer
            results.append(stats)
        
        # Tri par nombre de ventes
        results.sort(key=lambda x: x['trips_count'], reverse=True)
        
        return results
    
    @staticmethod
    def get_monthly_trends(agency_id: int, months: int = 12) -> Dict:
        """
        Évolution mensuelle du CA et des ventes
        
        Args:
            agency_id: ID de l'agence
            months: Nombre de mois à analyser
            
        Returns:
            Dict avec données mensuelles
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 31)
        
        trips = Trip.query.filter(
            Trip.agency_id == agency_id,
            Trip.status == 'sold',
            Trip.sold_at >= start_date
        ).all()
        
        # Agrégation par mois
        monthly_data = {}
        for trip in trips:
            if not trip.sold_at:
                continue
            
            month_key = trip.sold_at.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'month': month_key,
                    'trips_count': 0,
                    'revenue': 0
                }
            monthly_data[month_key]['trips_count'] += 1
            monthly_data[month_key]['revenue'] += trip.price
        
        # Trier chronologiquement
        sorted_data = sorted(monthly_data.values(), key=lambda x: x['month'])
        
        return {
            'months': [d['month'] for d in sorted_data],
            'trips_count': [d['trips_count'] for d in sorted_data],
            'revenue': [d['revenue'] for d in sorted_data]
        }
    
    @staticmethod
    def _get_top_destinations(trips: List[Trip], limit: int = 5) -> List[Dict]:
        """Méthode helper pour extraire top destinations"""
        destinations = {}
        for trip in trips:
            dest = trip.destination
            destinations[dest] = destinations.get(dest, 0) + 1
        
        sorted_dests = sorted(destinations.items(), key=lambda x: x[1], reverse=True)
        return [{'destination': d[0], 'count': d[1]} for d in sorted_dests[:limit]]
    
    @staticmethod
    def create_sales_report(
        agency_id: int,
        report_type: str,
        period_start: date,
        period_end: date,
        user_id: Optional[int] = None
    ) -> SalesReport:
        """
        Crée et sauvegarde un rapport de ventes
        
        Args:
            agency_id: ID de l'agence
            report_type: Type de rapport (daily, weekly, monthly, etc.)
            period_start: Date de début
            period_end: Date de fin
            user_id: ID du vendeur (None = rapport global)
            
        Returns:
            Objet SalesReport créé
        """
        # Récupérer les données
        query = Trip.query.filter(
            Trip.agency_id == agency_id,
            Trip.status == 'sold',
            Trip.sold_at >= datetime.combine(period_start, datetime.min.time()),
            Trip.sold_at <= datetime.combine(period_end, datetime.max.time())
        )
        
        if user_id:
            query = query.filter(Trip.user_id == user_id)
        
        trips = query.all()
        
        # Calculs
        total_sales = len(trips)
        total_revenue = sum(t.price for t in trips)
        average_sale = total_revenue // total_sales if total_sales > 0 else 0
        
        # Données détaillées (JSON)
        detailed_data = {
            'destinations': AnalyticsService._get_top_destinations(trips, limit=10),
            'daily_breakdown': {},
            'seller_breakdown': {} if not user_id else None
        }
        
        # Breakdown par vendeur (si rapport global)
        if not user_id:
            seller_stats = {}
            for trip in trips:
                seller_id = trip.user_id
                if seller_id not in seller_stats:
                    seller_stats[seller_id] = {
                        'pseudo': trip.user.pseudo,
                        'count': 0,
                        'revenue': 0
                    }
                seller_stats[seller_id]['count'] += 1
                seller_stats[seller_id]['revenue'] += trip.price
            detailed_data['seller_breakdown'] = seller_stats
        
        # Créer le rapport
        report = SalesReport(
            agency_id=agency_id,
            user_id=user_id,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            total_sales=total_sales,
            total_revenue=total_revenue,
            average_sale=average_sale,
            trip_count=Trip.query.filter(
                Trip.agency_id == agency_id,
                Trip.created_at >= datetime.combine(period_start, datetime.min.time()),
                Trip.created_at <= datetime.combine(period_end, datetime.max.time())
            ).count(),
            detailed_data=detailed_data
        )
        
        db.session.add(report)
        db.session.commit()
        
        return report
