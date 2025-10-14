# config.py - Configuration de l'Application Odyssée SaaS
import os
from datetime import timedelta

class Config:
    """Configuration de base de l'application Flask."""
    
    # ==============================================================================
    # SÉCURITÉ
    # ==============================================================================
    
    # Clé secrète pour les sessions Flask (DOIT être changée en production)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-2025'
    
    # Clé maître pour chiffrer/déchiffrer les configs des agences
    # CRITIQUE: Cette clé doit être la même partout sinon les données chiffrées sont perdues
    MASTER_ENCRYPTION_KEY = os.environ.get('MASTER_ENCRYPTION_KEY') or 'dev-master-key-CHANGE-THIS'
    
    # ==============================================================================
    # BASE DE DONNÉES
    # ==============================================================================
    
    # URL de la base de données
    # En production (Railway) : PostgreSQL automatique via DATABASE_URL
    # En développement : SQLite local
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///odyssee.db'
    
    # Fix pour PostgreSQL sur Railway (remplace postgres:// par postgresql://)
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Vérifie la connexion avant de l'utiliser
        'pool_recycle': 300,     # Recycle les connexions après 5 minutes
    }
    
    # ==============================================================================
    # SESSION
    # ==============================================================================
    
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # ==============================================================================
    # CORS (pour les API)
    # ==============================================================================
    
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # ==============================================================================
    # UPLOADS & FILES
    # ==============================================================================
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max pour les uploads
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
    
    # ==============================================================================
    # CONFIGURATION PAR DÉFAUT SUPER-ADMIN
    # ==============================================================================
    
    # Ces infos sont utilisées pour créer le compte super-admin au premier démarrage
    SUPER_ADMIN_USERNAME = os.environ.get('SUPER_ADMIN_USERNAME') or 'superadmin'
    SUPER_ADMIN_PASSWORD = os.environ.get('SUPER_ADMIN_PASSWORD') or 'ChangeMe2025!'
    SUPER_ADMIN_EMAIL = os.environ.get('SUPER_ADMIN_EMAIL') or 'admin@odyssee-saas.com'
    
    # ==============================================================================
    # LIMITES & QUOTAS PAR DÉFAUT
    # ==============================================================================
    
    DEFAULT_MONTHLY_GENERATION_LIMIT = 100  # Par agence
    DEFAULT_DAILY_SELLER_LIMIT = 5          # Par vendeur
    DEFAULT_SELLER_MARGIN_PERCENTAGE = 80   # % de marge pour le vendeur
    
    # ==============================================================================
    # CONFIGURATION MAIL PAR DÉFAUT (optionnel)
    # ==============================================================================
    
    # Ces paramètres peuvent être surchargés par agence
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or MAIL_USERNAME
    
    # ==============================================================================
    # TEMPLATES & BRANDING
    # ==============================================================================
    
    AVAILABLE_TEMPLATES = ['classic', 'modern', 'luxury']
    DEFAULT_TEMPLATE = 'classic'
    DEFAULT_PRIMARY_COLOR = '#3B82F6'
    
    # ==============================================================================
    # PUBLICATION (URLs de base)
    # ==============================================================================
    
    # URL publique de base (ex: https://odyssee-saas.com)
    SITE_PUBLIC_URL = os.environ.get('SITE_PUBLIC_URL') or 'http://localhost:5000'
    
    # ==============================================================================
    # STRIPE (optionnel, peut être configuré par agence)
    # ==============================================================================
    
    STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    # ==============================================================================
    # DÉVELOPPEMENT & DEBUG
    # ==============================================================================
    
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'
    TESTING = False


class DevelopmentConfig(Config):
    """Configuration spécifique au développement."""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # Mettre True pour voir les requêtes SQL


class ProductionConfig(Config):
    """Configuration spécifique à la production."""
    DEBUG = False
    TESTING = False
    
    # En production, ces variables DOIVENT être définies
    @classmethod
    def validate(cls):
        """Vérifie que les variables critiques sont définies."""
        required_vars = ['SECRET_KEY', 'MASTER_ENCRYPTION_KEY']
        missing = [var for var in required_vars if not os.environ.get(var)]
        
        if missing:
            raise ValueError(f"❌ Variables d'environnement manquantes en production: {', '.join(missing)}")


# ==============================================================================
# SÉLECTION AUTOMATIQUE DE LA CONFIG
# ==============================================================================

def get_config():
    """Retourne la configuration appropriée selon l'environnement."""
    env = os.environ.get('FLASK_ENV', 'development')
    
    if env == 'production':
        ProductionConfig.validate()
        return ProductionConfig
    else:
        return DevelopmentConfig


# Export de la config active
active_config = get_config()