# schemas.py - Modèles de validation Pydantic

from pydantic import BaseModel, EmailStr, HttpUrl, constr, conint, Field, ValidationError
from typing import Optional, Dict, Any

# ==============================================================================
# SCHÉMAS POUR LES AGENCES
# ==============================================================================

class AgencyBaseSchema(BaseModel):
    """Champs communs pour la création et la mise à jour d'une agence."""
    name: constr(min_length=1)
    subdomain: constr(min_length=3, regex=r'^[a-z0-9-]+$') # Alphanum + hyphen
    contact_email: EmailStr
    logo_url: Optional[HttpUrl] = None
    primary_color: Optional[constr(regex=r'^#[0-9a-fA-F]{6}$')] = '#3B82F6'
    template_name: Optional[str] = 'classic'
    contact_phone: Optional[str] = None
    contact_address: Optional[str] = None
    manual_payment_email_template: Optional[str] = None
    website_url: Optional[HttpUrl] = None
    subscription_tier: Optional[str] = 'basic'
    monthly_generation_limit: conint(ge=0) = 100
    is_active: bool = True

    # Champs pour les configurations chiffrées (acceptent n'importe quelle valeur valide)
    google_api_key: Optional[str] = None
    stripe_api_key: Optional[str] = None
    mail_config: Optional[Dict[str, Any]] = None
    ftp_config: Optional[Dict[str, Any]] = None

class AgencyCreateSchema(AgencyBaseSchema):
    """Schéma pour la création d'une agence. Tous les champs de base sont requis."""
    name: constr(min_length=1)
    subdomain: constr(min_length=3, regex=r'^[a-z0-9-]+$')
    contact_email: EmailStr

class AgencyUpdateSchema(AgencyBaseSchema):
    """
    Schéma pour la mise à jour d'une agence.
    Tous les champs sont optionnels.
    """
    name: Optional[constr(min_length=1)] = None
    subdomain: Optional[constr(min_length=3, regex=r'^[a-z0-9-]+$')] = None
    contact_email: Optional[EmailStr] = None
    monthly_generation_limit: Optional[conint(ge=0)] = None
    is_active: Optional[bool] = None

    class Config:
        extra = 'ignore' # Ignore les champs non définis dans le schéma