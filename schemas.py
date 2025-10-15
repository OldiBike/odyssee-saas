# schemas.py - Schémas de validation Pydantic pour l'API
"""
Schémas de validation des données d'entrée pour les API.
Utilise Pydantic pour une validation stricte et automatique.
"""

from pydantic import BaseModel, EmailStr, HttpUrl, validator, Field
from typing import Optional, Dict, Any

# ==============================================================================
# SCHÉMAS POUR LES AGENCES
# ==============================================================================

class AgencyCreateSchema(BaseModel):
    """Schéma de validation pour la création d'une agence."""
    
    # Champs obligatoires
    name: str = Field(..., min_length=2, max_length=200, description="Nom de l'agence")
    subdomain: str = Field(..., min_length=2, max_length=100, description="Sous-domaine unique")
    contact_email: EmailStr = Field(..., description="Email de contact")
    
    # Branding
    logo_url: Optional[HttpUrl] = Field(None, description="URL du logo")
    primary_color: str = Field('#3B82F6', pattern=r'^#[0-9A-Fa-f]{6}$', description="Couleur primaire (hex)")
    template_name: str = Field('classic', description="Nom du template")
    
    # Informations de contact
    contact_phone: Optional[str] = Field(None, max_length=50, description="Téléphone de contact")
    contact_address: Optional[str] = Field(None, description="Adresse de l'agence")
    manual_payment_email_template: Optional[str] = Field(None, description="Template email paiement manuel")
    website_url: Optional[HttpUrl] = Field(None, description="URL du site web")
    
    # Business
    subscription_tier: str = Field('basic', description="Niveau d'abonnement")
    monthly_generation_limit: int = Field(100, ge=0, le=10000, description="Limite mensuelle de générations")
    
    # Configs chiffrées (optionnelles)
    google_api_key: Optional[str] = Field(None, description="Clé API Google")
    stripe_api_key: Optional[str] = Field(None, description="Clé API Stripe")
    mail_config: Optional[Dict[str, Any]] = Field(None, description="Configuration email")
    ftp_config: Optional[Dict[str, Any]] = Field(None, description="Configuration FTP/SFTP")
    
    @validator('subdomain')
    def subdomain_alphanumeric(cls, v):
        """Vérifie que le subdomain ne contient que des caractères alphanumériques et tirets."""
        if not v.replace('-', '').isalnum():
            raise ValueError('Le sous-domaine ne peut contenir que des lettres, chiffres et tirets')
        if v.startswith('-') or v.endswith('-'):
            raise ValueError('Le sous-domaine ne peut pas commencer ou finir par un tiret')
        return v.lower()
    
    @validator('template_name')
    def template_exists(cls, v):
        """Vérifie que le template existe."""
        allowed = ['classic', 'modern', 'luxury']
        if v not in allowed:
            raise ValueError(f'Template invalide. Choix possibles : {", ".join(allowed)}')
        return v
    
    @validator('subscription_tier')
    def tier_valid(cls, v):
        """Vérifie que le tier est valide."""
        allowed = ['basic', 'pro', 'enterprise']
        if v not in allowed:
            raise ValueError(f'Tier invalide. Choix possibles : {", ".join(allowed)}')
        return v
    
    @validator('mail_config', 'ftp_config')
    def config_structure(cls, v):
        """Vérifie la structure minimale des configs."""
        if v is not None and not isinstance(v, dict):
            raise ValueError('La configuration doit être un objet JSON valide')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Voyages Paradis",
                "subdomain": "voyages-paradis",
                "contact_email": "contact@voyages-paradis.com",
                "contact_phone": "+32 2 123 45 67",
                "primary_color": "#FF6B6B",
                "template_name": "luxury",
                "subscription_tier": "pro",
                "monthly_generation_limit": 500
            }
        }


class AgencyUpdateSchema(BaseModel):
    """Schéma de validation pour la mise à jour d'une agence.
    Tous les champs sont optionnels."""
    
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    subdomain: Optional[str] = Field(None, min_length=2, max_length=100)
    contact_email: Optional[EmailStr] = None
    
    logo_url: Optional[HttpUrl] = None
    primary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    template_name: Optional[str] = None
    
    contact_phone: Optional[str] = Field(None, max_length=50)
    contact_address: Optional[str] = None
    manual_payment_email_template: Optional[str] = None
    website_url: Optional[HttpUrl] = None
    
    is_active: Optional[bool] = None
    subscription_tier: Optional[str] = None
    monthly_generation_limit: Optional[int] = Field(None, ge=0, le=10000)
    
    google_api_key: Optional[str] = None
    stripe_api_key: Optional[str] = None
    mail_config: Optional[Dict[str, Any]] = None
    ftp_config: Optional[Dict[str, Any]] = None
    
    @validator('subdomain')
    def subdomain_alphanumeric(cls, v):
        if v is None:
            return v
        if not v.replace('-', '').isalnum():
            raise ValueError('Le sous-domaine ne peut contenir que des lettres, chiffres et tirets')
        if v.startswith('-') or v.endswith('-'):
            raise ValueError('Le sous-domaine ne peut pas commencer ou finir par un tiret')
        return v.lower()
    
    @validator('template_name')
    def template_exists(cls, v):
        if v is None:
            return v
        allowed = ['classic', 'modern', 'luxury']
        if v not in allowed:
            raise ValueError(f'Template invalide. Choix possibles : {", ".join(allowed)}')
        return v
    
    @validator('subscription_tier')
    def tier_valid(cls, v):
        if v is None:
            return v
        allowed = ['basic', 'pro', 'enterprise']
        if v not in allowed:
            raise ValueError(f'Tier invalide. Choix possibles : {", ".join(allowed)}')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Voyages Paradis SARL",
                "primary_color": "#00B4D8",
                "monthly_generation_limit": 1000
            }
        }


# ==============================================================================
# SCHÉMAS POUR LES UTILISATEURS (à ajouter si nécessaire)
# ==============================================================================

class UserCreateSchema(BaseModel):
    """Schéma pour la création d'un utilisateur."""
    username: str = Field(..., min_length=3, max_length=80)
    password: str = Field(..., min_length=8, max_length=100)
    pseudo: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    role: str = Field('seller', description="Rôle de l'utilisateur")
    margin_percentage: int = Field(80, ge=0, le=100)
    daily_generation_limit: int = Field(5, ge=1, le=10000, description="Limite quotidienne de génération (1-10000)")
    
    @validator('role')
    def role_valid(cls, v):
        allowed = ['agency_admin', 'seller']
        if v not in allowed:
            raise ValueError(f'Rôle invalide. Choix possibles : {", ".join(allowed)}')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        """Vérifie la force du mot de passe."""
        if len(v) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
        # Optionnel : ajouter d'autres règles de complexité
        return v


class UserUpdateSchema(BaseModel):
    """Schéma pour la mise à jour d'un utilisateur."""
    username: Optional[str] = Field(None, min_length=3, max_length=80)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    pseudo: Optional[str] = Field(None, min_length=2, max_length=80)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    role: Optional[str] = None
    margin_percentage: Optional[int] = Field(None, ge=0, le=100)
    daily_generation_limit: Optional[int] = Field(None, ge=1, le=10000, description="Limite quotidienne de génération (1-10000)")
    is_active: Optional[bool] = None
    
    @validator('role')
    def role_valid(cls, v):
        if v is None:
            return v
        allowed = ['agency_admin', 'seller']
        if v not in allowed:
            raise ValueError(f'Rôle invalide. Choix possibles : {", ".join(allowed)}')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
        return v


# ==============================================================================
# SCHÉMAS POUR LES CLIENTS (à ajouter si nécessaire)
# ==============================================================================

class ClientCreateSchema(BaseModel):
    """Schéma pour la création d'un client."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
