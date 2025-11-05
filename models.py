# models.py - Application SaaS Multi-Agences Odyssée
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from cryptography.fernet import Fernet
import json
import os

db = SQLAlchemy()

# ==============================================================================
# MODÈLE AGENCY - Cœur du système multi-tenant
# ==============================================================================

class Agency(db.Model):
    """
    Représente une agence de voyages utilisant la plateforme.
    Chaque agence a ses propres configurations, branding et données isolées.
    """
    id = db.Column(db.Integer, primary_key=True)
    
    # Identification
    name = db.Column(db.String(200), nullable=False)
    subdomain = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # Branding & Personnalisation
    logo_url = db.Column(db.String(500))
    primary_color = db.Column(db.String(7), default='#3B82F6')  # Format hex
    secondary_color = db.Column(db.String(7), default='#2c3e50') # NOUVEAU
    template_name = db.Column(db.String(50), default='classic')  # classic/modern/luxury
    
    # Configurations API (CHIFFRÉES - ne jamais stocker en clair)
    google_api_key_encrypted = db.Column(db.Text)
    stripe_api_key_encrypted = db.Column(db.Text)
    mail_config_encrypted = db.Column(db.Text)  # JSON chiffré contenant tous les params mail
    ftp_config_encrypted = db.Column(db.Text)   # JSON chiffré pour SFTP/FTP
    
    # Configuration Email Sync (OAuth2)
    email_sync_enabled = db.Column(db.Boolean, default=False)
    email_provider = db.Column(db.String(20))  # 'gmail' ou 'outlook'
    email_access_token_encrypted = db.Column(db.Text)  # Token OAuth chiffré
    email_refresh_token_encrypted = db.Column(db.Text)  # Refresh token chiffré
    email_token_expiry = db.Column(db.DateTime)
    email_sync_address = db.Column(db.String(255))  # Adresse email à synchroniser
    last_email_sync = db.Column(db.DateTime)
    email_sync_history_id = db.Column(db.String(100))  # Pour Gmail History API
    
    # Configuration Email Sync Manuel (SMTP/IMAP)
    smtp_config_encrypted = db.Column(db.Text)  # Configuration SMTP chiffrée
    imap_config_encrypted = db.Column(db.Text)  # Configuration IMAP chiffrée
    email_config_type = db.Column(db.String(20))  # 'oauth' ou 'manual'
    email_sync_provider = db.Column(db.String(50))  # 'gmail', 'outlook', 'manual'
    email_sync_email = db.Column(db.String(255))  # Adresse email pour sync manuel
    email_last_sync_at = db.Column(db.DateTime)  # Dernière synchronisation
    
    # Configuration Synchronisation Automatique (Phase 3A)
    auto_sync_enabled = db.Column(db.Boolean, default=False)
    sync_frequency = db.Column(db.String(20), default='hourly')  # hourly, daily, manual
    last_auto_sync_at = db.Column(db.DateTime)
    auto_sync_errors_count = db.Column(db.Integer, default=0)
    
    # Configuration Webhooks Gmail (Phase 3D)
    gmail_watch_expiration = db.Column(db.DateTime)
    gmail_history_id = db.Column(db.BigInteger)
    webhook_secret = db.Column(db.String(255))  # Secret pour validation webhook
    
    # Informations de contact (affichées dans les fiches de voyage)
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(50))
    contact_address = db.Column(db.Text) # NOUVEAU
    manual_payment_email_template = db.Column(db.Text) # Template pour l'email de paiement manuel
    website_url = db.Column(db.String(255))
    
    # Business & Limites
    is_active = db.Column(db.Boolean, default=True)
    subscription_tier = db.Column(db.String(50), default='basic')  # basic/pro/enterprise
    monthly_generation_limit = db.Column(db.Integer, default=100)
    current_month_usage = db.Column(db.Integer, default=0)
    usage_reset_date = db.Column(db.Date, default=date.today)
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    users = db.relationship('User', backref='agency', lazy=True, cascade='all, delete-orphan')
    trips = db.relationship('Trip', backref='agency', lazy=True, cascade='all, delete-orphan')
    clients = db.relationship('Client', backref='agency', lazy=True, cascade='all, delete-orphan')
    activities = db.relationship('ActivityLog', backref='agency', lazy=True, cascade='all, delete-orphan', order_by="ActivityLog.created_at.desc()")
    social_campaigns = db.relationship('SocialMediaCampaign', backref='agency')
    social_templates = db.relationship('SocialMediaTemplate', backref='agency')
    
    def to_dict(self):
        """Représentation JSON (sans les données sensibles)"""
        return {
            'id': self.id,
            'name': self.name,
            'subdomain': self.subdomain,
            'logo_url': self.logo_url,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'template_name': self.template_name,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'contact_address': self.contact_address, # NOUVEAU
            'manual_payment_email_template': self.manual_payment_email_template,
            'is_active': self.is_active,
            'subscription_tier': self.subscription_tier,
            'monthly_limit': self.monthly_generation_limit,
            'current_usage': self.current_month_usage
        }
    
    def __repr__(self):
        return f'<Agency {self.name} ({self.subdomain})>'


# ==============================================================================
# MODÈLE USER - Utilisateurs multi-rôles
# ==============================================================================

class User(db.Model):
    """
    Utilisateurs avec 3 niveaux d'accès :
    - super_admin : Gère toute la plateforme
    - agency_admin : Gère son agence
    - seller : Vendeur dans une agence
    """
    id = db.Column(db.Integer, primary_key=True)
    
    # Liaison à l'agence (NULL pour super_admin uniquement)
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id'), nullable=True, index=True)
    
    # Authentification
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)  # Hash bcrypt
    
    # Informations
    pseudo = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(50))
    
    # Rôles & Permissions
    role = db.Column(db.String(20), nullable=False, default='seller')  # super_admin/agency_admin/seller
    margin_percentage = db.Column(db.Integer, default=80)  # % de marge gardée par le vendeur
    
    # Quotas de génération (pour les vendeurs)
    generation_count = db.Column(db.Integer, default=0)
    last_generation_date = db.Column(db.Date, default=date.today)
    daily_generation_limit = db.Column(db.Integer, default=5)
    
    # NOUVEAU : Gestion des vendeurs
    sales_target = db.Column(db.Integer)  # Objectif mensuel en €
    commission_rate = db.Column(db.Integer, default=10)  # % commission sur les ventes
    is_team_leader = db.Column(db.Boolean, default=False)
    team_id = db.Column(db.Integer, db.ForeignKey('sales_teams.id'))
    
    # Métadonnées
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relations
    trips = db.relationship('Trip', backref='user', lazy=True)
    interactions = db.relationship('ClientInteraction', foreign_keys='ClientInteraction.user_id', backref='user', lazy=True)
    read_interactions = db.relationship('ClientInteraction', foreign_keys='ClientInteraction.read_by_user_id', backref='read_by', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'agency_id': self.agency_id,
            'username': self.username,
            'pseudo': self.pseudo,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'margin_percentage': self.margin_percentage,
            'generation_usage': f"{self.generation_count} / {self.daily_generation_limit}",
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


# ==============================================================================
# MODÈLE CLIENT - Clients des agences
# ==============================================================================

class Client(db.Model):
    """Clients finaux qui achètent des voyages."""
    id = db.Column(db.Integer, primary_key=True)
    
    # Liaison à l'agence
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id'), nullable=False, index=True)
    
    # Informations client
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True, index=True)
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    
    # NOUVEAU : CRM avancé
    client_type = db.Column(db.String(20), default='nouveau')  # nouveau, regulier, vip
    total_purchases = db.Column(db.Integer, default=0)  # Nombre d'achats
    total_revenue = db.Column(db.Integer, default=0)    # CA total généré
    last_purchase_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)  # Notes générales sur le client
    source = db.Column(db.String(50))  # facebook, referral, direct, website, etc.
    birthday = db.Column(db.Date)
    preferences = db.Column(db.JSON)  # Destinations préférées, budget, etc.
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    trips = db.relationship('Trip', backref='client', lazy=True)
    interactions = db.relationship('ClientInteraction', backref='client', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'agency_id': self.agency_id,
            'full_name': f"{self.first_name} {self.last_name}",
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address
        }
    
    def __repr__(self):
        return f'<Client {self.first_name} {self.last_name}>'


# ==============================================================================
# MODÈLE TRIP - Voyages créés
# ==============================================================================

class Trip(db.Model):
    """Représente un voyage créé/proposé/vendu."""
    id = db.Column(db.Integer, primary_key=True)
    
    # Liaisons
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True, index=True)
    
    # Données complètes du voyage (JSON)
    full_data_json = db.Column(db.Text, nullable=False)
    
    # Informations principales (pour requêtes rapides)
    hotel_name = db.Column(db.String(200), nullable=False, index=True)
    destination = db.Column(db.String(200), nullable=False, index=True)
    price = db.Column(db.Integer, nullable=False)
    
    # Status du voyage
    status = db.Column(db.String(50), nullable=False, default='proposed', index=True)
    # Valeurs possibles: proposed, assigned, sold
    
    # Publication
    is_published = db.Column(db.Boolean, default=False)
    published_filename = db.Column(db.String(255))
    is_ultra_budget = db.Column(db.Boolean, nullable=False, default=False)
    is_day_trip = db.Column(db.Boolean, default=False)

    # Champs spécifiques aux excursions
    transport_type = db.Column(db.String(50))
    bus_departure_address = db.Column(db.String(255))
    travel_duration_minutes = db.Column(db.Integer)
    departure_time = db.Column(db.String(5)) # HH:MM
    return_time = db.Column(db.String(5))    # HH:MM
    
    # Page client privée
    client_published_filename = db.Column(db.String(255))
    
    # Paiement
    stripe_payment_link = db.Column(db.Text)
    down_payment_amount = db.Column(db.Integer)
    payment_method = db.Column(db.String(50)) # 'stripe' ou 'manual'
    down_payment_status = db.Column(db.String(50)) # 'requested', 'paid'
    balance_due_date = db.Column(db.Date)
    
    # Documents attachés
    document_filenames = db.Column(db.Text)  # Liste séparée par virgules
    
    # Dates importantes
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    assigned_at = db.Column(db.DateTime)
    sold_at = db.Column(db.DateTime, index=True)
    
    # Relations
    invoices = db.relationship('Invoice', backref='trip', lazy=True, cascade="all, delete-orphan")
    notes = db.relationship('TripNote', backref='trip', lazy=True, cascade="all, delete-orphan", order_by="TripNote.created_at.desc()")
    social_campaigns = db.relationship('SocialMediaCampaign', backref='trip', cascade="all, delete-orphan")
    
    def to_dict(self):
        """Représentation JSON du voyage."""
        full_data = json.loads(self.full_data_json)
        form_data = full_data.get('form_data', {})
        
        client_full_name = None
        client_email = None
        client_phone = None
        
        if self.client:
            client_full_name = self.client.to_dict()['full_name']
            client_email = self.client.email
            client_phone = self.client.phone
        
        return {
            'id': self.id,
            'agency_id': self.agency_id,
            'user_id': self.user_id,
            'creator_pseudo': self.user.pseudo if self.user else 'N/A',
            'hotel_name': self.hotel_name,
            'destination': self.destination,
            'price': self.price,
            'status': self.status,
            'is_published': self.is_published,
            'published_filename': self.published_filename,
            'is_ultra_budget': self.is_ultra_budget,
            'client_published_filename': self.client_published_filename,
            'client_full_name': client_full_name,
            'client_email': client_email,
            'client_phone': client_phone,
            'created_at': self.created_at.strftime('%d/%m/%Y'),
            'assigned_at': self.assigned_at.strftime('%d/%m/%Y') if self.assigned_at else None,
            'sold_at': self.sold_at.strftime('%d/%m/%Y') if self.sold_at else None,
            'down_payment_amount': self.down_payment_amount,
            'balance_due_date': self.balance_due_date.strftime('%Y-%m-%d') if self.balance_due_date else None,
            'date_start': form_data.get('date_start'),
            'date_end': form_data.get('date_end'),
            'document_filenames': self.document_filenames.split(',') if self.document_filenames else [],
            'invoices': [invoice.to_dict() for invoice in self.invoices]
        }
    
    def __repr__(self):
        return f'<Trip {self.id}: {self.hotel_name} - {self.status}>'


# ==============================================================================
# MODÈLE INVOICE - Factures
# ==============================================================================

class Invoice(db.Model):
    """Factures générées pour les voyages vendus."""
    id = db.Column(db.Integer, primary_key=True)
    
    # Numéro unique de facture
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Liaison au voyage
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False, index=True)
    
    # Date de création
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'created_at': self.created_at.strftime('%d/%m/%Y')
        }
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'


# ==============================================================================
# MODÈLE ACTIVITYLOG - Journal d'activités de l'agence
# ==============================================================================

class ActivityLog(db.Model):
    """Journal des activités importantes au sein d'une agence."""
    id = db.Column(db.Integer, primary_key=True)
    
    # Liaisons
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=True, index=True)
    
    # Description de l'action
    action = db.Column(db.String(100), nullable=False, index=True) # Ex: 'trip_created', 'trip_sold'
    details = db.Column(db.String(255)) # Ex: "Voyage à Paris"
    
    # Date de création
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relations
    user = db.relationship('User', backref='activities')
    trip = db.relationship('Trip', backref='activities')

    def to_dict(self):
        return {
            'id': self.id,
            'user_pseudo': self.user.pseudo,
            'action': self.action,
            'details': self.details,
            'trip_id': self.trip_id,
            'trip_destination': self.trip.destination if self.trip else None,
            'created_at': self.created_at.strftime('%d/%m/%Y à %H:%M')
        }


# ==============================================================================
# MODÈLE TRIPNOTE - Notes internes sur un voyage
# ==============================================================================

class TripNote(db.Model):
    """Notes internes laissées par les utilisateurs sur un voyage."""
    id = db.Column(db.Integer, primary_key=True)
    
    # Contenu de la note
    content = db.Column(db.Text, nullable=False)
    
    # Liaisons
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Date de création
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relation pour récupérer l'auteur de la note
    author = db.relationship('User', backref='notes')

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'author_pseudo': self.author.pseudo,
            'created_at': self.created_at.strftime('%d/%m/%Y à %H:%M')
        }

# ==============================================================================
# MODÈLE SOCIAL MEDIA CAMPAIGN - Campagnes pour les réseaux sociaux
# ==============================================================================

class SocialMediaCampaign(db.Model):
    """Stores social media campaigns for trips"""
    __tablename__ = 'social_media_campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Campaign details
    campaign_name = db.Column(db.String(200))
    platform = db.Column(db.String(50))  # instagram, facebook, multi
    format = db.Column(db.String(50))  # carousel, story, post
    status = db.Column(db.String(50), default='draft')  # draft, generated, published
    
    # Generated content
    slides_data = db.Column(db.JSON)  # Array of slide URLs and metadata
    captions = db.Column(db.JSON)  # Platform-specific captions
    hashtags = db.Column(db.Text)
    
    # Performance tracking
    published_at = db.Column(db.DateTime)
    performance_metrics = db.Column(db.JSON)

class SocialMediaTemplate(db.Model):
    """Agency-specific social media templates"""
    __tablename__ = 'social_media_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id'), nullable=False)
    name = db.Column(db.String(100))
    platform = db.Column(db.String(50))
    
    # Design settings
    primary_color = db.Column(db.String(7))  # Hex color
    secondary_color = db.Column(db.String(7))
    font_family = db.Column(db.String(100), default='Montserrat')
    logo_position = db.Column(db.String(20), default='top-right')  # top-left, top-right, bottom-left, bottom-right
    
    # Text templates
    caption_template = db.Column(db.Text)
    hashtag_template = db.Column(db.Text)

# ==============================================================================
# MODÈLES CRM & ANALYTICS - Nouveaux modules
# ==============================================================================

class ClientInteraction(db.Model):
    """Historique des interactions avec les clients (CRM)"""
    __tablename__ = 'client_interactions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Liaisons
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Type d'interaction
    interaction_type = db.Column(db.String(50), nullable=False, index=True)  # appel, email, meeting, note
    
    # Contenu
    content = db.Column(db.Text)
    
    # Champs spécifiques aux emails (pour interaction_type='email')
    email_message_id = db.Column(db.String(255), index=True)  # ID unique de l'email
    email_thread_id = db.Column(db.String(255), index=True)  # ID du thread
    email_subject = db.Column(db.String(500))
    email_from = db.Column(db.String(255))
    email_to = db.Column(db.String(255))
    email_cc = db.Column(db.Text)
    is_outbound = db.Column(db.Boolean, default=False)  # True si envoyé par l'agence
    ai_summary = db.Column(db.Text)  # Résumé généré par IA
    
    # Champs pour les notifications (tracking de lecture)
    is_read = db.Column(db.Boolean, default=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    read_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        result = {
            'id': self.id,
            'client_id': self.client_id,
            'user_id': self.user_id,
            'user_pseudo': self.user.pseudo if self.user else 'N/A',
            'interaction_type': self.interaction_type,
            'content': self.content,
            'created_at': self.created_at.strftime('%d/%m/%Y à %H:%M')
        }
        
        # Ajouter les champs email si présents
        if self.interaction_type == 'email':
            result.update({
                'email_message_id': self.email_message_id,
                'email_thread_id': self.email_thread_id,
                'email_subject': self.email_subject,
                'email_from': self.email_from,
                'email_to': self.email_to,
                'email_cc': self.email_cc,
                'is_outbound': self.is_outbound,
                'ai_summary': self.ai_summary
            })
        
        return result
    
    def __repr__(self):
        return f'<ClientInteraction {self.id}: {self.interaction_type}>'


class SalesReport(db.Model):
    """Rapports de ventes générés"""
    __tablename__ = 'sales_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Liaisons
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)  # Null = rapport global
    
    # Configuration du rapport
    report_type = db.Column(db.String(50), nullable=False)  # daily, weekly, monthly, yearly, custom
    period_start = db.Column(db.Date, nullable=False, index=True)
    period_end = db.Column(db.Date, nullable=False, index=True)
    
    # Métriques principales
    total_sales = db.Column(db.Integer, default=0)  # Nombre de ventes
    total_revenue = db.Column(db.Integer, default=0)  # CA total
    average_sale = db.Column(db.Integer, default=0)  # Panier moyen
    trip_count = db.Column(db.Integer, default=0)  # Nombre de voyages créés
    
    # Données détaillées (JSON)
    detailed_data = db.Column(db.JSON)  # Stats par vendeur, destinations, etc.
    
    # Métadonnées
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    agency = db.relationship('Agency', backref='sales_reports')
    user = db.relationship('User', backref='sales_reports')
    
    def to_dict(self):
        return {
            'id': self.id,
            'agency_id': self.agency_id,
            'user_id': self.user_id,
            'user_pseudo': self.user.pseudo if self.user else 'Global',
            'report_type': self.report_type,
            'period_start': self.period_start.strftime('%d/%m/%Y'),
            'period_end': self.period_end.strftime('%d/%m/%Y'),
            'total_sales': self.total_sales,
            'total_revenue': self.total_revenue,
            'average_sale': self.average_sale,
            'trip_count': self.trip_count,
            'generated_at': self.generated_at.strftime('%d/%m/%Y à %H:%M')
        }
    
    def __repr__(self):
        return f'<SalesReport {self.id}: {self.report_type} - {self.period_start} to {self.period_end}>'


class SalesTeam(db.Model):
    """Équipes commerciales"""
    __tablename__ = 'sales_teams'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Liaison
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id'), nullable=False, index=True)
    
    # Informations de l'équipe
    name = db.Column(db.String(100), nullable=False)
    leader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    agency = db.relationship('Agency', backref='sales_teams')
    leader = db.relationship('User', foreign_keys=[leader_id], backref='led_team')
    members = db.relationship('User', foreign_keys='User.team_id', backref='team')
    
    def to_dict(self):
        return {
            'id': self.id,
            'agency_id': self.agency_id,
            'name': self.name,
            'leader_id': self.leader_id,
            'leader_name': self.leader.pseudo if self.leader else None,
            'member_count': len(self.members),
            'created_at': self.created_at.strftime('%d/%m/%Y')
        }
    
    def __repr__(self):
        return f'<SalesTeam {self.name}>'
