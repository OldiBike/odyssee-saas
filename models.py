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
    template_name = db.Column(db.String(50), default='classic')  # classic/modern/luxury
    
    # Configurations API (CHIFFRÉES - ne jamais stocker en clair)
    google_api_key_encrypted = db.Column(db.Text)
    stripe_api_key_encrypted = db.Column(db.Text)
    mail_config_encrypted = db.Column(db.Text)  # JSON chiffré contenant tous les params mail
    ftp_config_encrypted = db.Column(db.Text)   # JSON chiffré pour SFTP/FTP
    
    # Informations de contact (affichées dans les fiches de voyage)
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(50))
    contact_address = db.Column(db.Text)
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
    
    def to_dict(self):
        """Représentation JSON (sans les données sensibles)"""
        return {
            'id': self.id,
            'name': self.name,
            'subdomain': self.subdomain,
            'logo_url': self.logo_url,
            'primary_color': self.primary_color,
            'template_name': self.template_name,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
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
    
    # Métadonnées
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relations
    trips = db.relationship('Trip', backref='user', lazy=True)
    
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
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    trips = db.relationship('Trip', backref='client', lazy=True)
    
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
    
    # Page client privée
    client_published_filename = db.Column(db.String(255))
    
    # Paiement
    stripe_payment_link = db.Column(db.Text)
    down_payment_amount = db.Column(db.Integer)
    balance_due_date = db.Column(db.Date)
    
    # Documents attachés
    document_filenames = db.Column(db.Text)  # Liste séparée par virgules
    
    # Dates importantes
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    assigned_at = db.Column(db.DateTime)
    sold_at = db.Column(db.DateTime, index=True)
    
    # Relations
    invoices = db.relationship('Invoice', backref='trip', lazy=True, cascade="all, delete-orphan")
    
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