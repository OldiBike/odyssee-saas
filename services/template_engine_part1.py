# services/template_engine.py
"""
Moteur de génération de templates HTML pour les fiches de voyage.
Version complète adaptée d'odyssee-app - génère des fiches au style Instagram moderne.
"""

from typing import Dict, Any
from datetime import datetime
import re
import unidecode


def render_trip_template(data: Dict[str, Any], 
                        template_type: str,
                        agency_style: str,
                        agency_config: Dict[str, Any]) -> str:
    """
    Génère le HTML complet d'une fiche de voyage au style Instagram moderne.
    Identique à odyssee-app mais avec personnalisation par agence.
    
    Args:
        data: Données complètes (form_data + api_data + savings)
        template_type: 'standard' ou 'day_trip' (pour l'instant, on génère le style standard)
        agency_style: Style du template (non utilisé pour l'instant, toujours Instagram style)
        agency_config: Configuration de l'agence (logo, couleurs, contact)
        
    Returns:
        HTML complet de la fiche
    """
    form_data = data.get('form_data', {})
    api_data = data.get('api_data', {})
    savings = data.get('savings', 0)
    comparison_total = data.get('comparison_total', 0)
    
    # Déterminer si c'est une excursion d'un jour
    is_day_trip = form_data.get('is_day_trip', False)
    
    if is_day_trip:
        return generate_day_trip_page_html(
            form_data,
            api_data,
            agency_config
        )
    else:
        return generate_travel_page_html(
            form_data, 
            api_data, 
            savings, 
            comparison_total,
            agency_config
        )
