# services/template_engine.py
"""
Moteur de génération de templates HTML pour les fiches de voyage
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, time


class TemplateEngine:
    """Générateur de templates HTML pour les fiches de voyage"""
    
    # Templates disponibles
    TEMPLATES = {
        'classic': 'template_classic',
        'modern': 'template_modern', 
        'luxury': 'template_luxury'
    }
    
    def __init__(self, agency_config: Dict[str, Any]) -> None:
        """
        Initialise le moteur de templates
        
        Args:
            agency_config: Configuration de l'agence (nom, couleurs, logo, etc.)
        """
        self.agency_config = agency_config
        self.primary_color = agency_config.get('primary_color', '#3B82F6')
        self.agency_name = agency_config.get('name', 'Agence de Voyages')
        self.logo_url = agency_config.get('logo_url', '')
        self.contact_email = agency_config.get('contact_email', '')
        self.contact_phone = agency_config.get('contact_phone', '')
    
    def render_trip_template(self, trip_data: Dict[str, Any], 
                           template_type: str = 'standard',
                           style: Optional[str] = 'classic') -> str:
        """
        Génère le HTML complet de la fiche de voyage
        
        Args:
            trip_data: Toutes les données du voyage (form_data + api_data)
            template_type: Type de template ('standard' ou 'day_trip')
            style: Style du template ('classic', 'modern', 'luxury')
            
        Returns:
            HTML complet de la fiche
        """
        
        # Sélectionner la méthode de rendu selon le style
        render_method = getattr(self, f'_{self.TEMPLATES.get(style, "template_classic")}', None)
        
        if not render_method:
            render_method = self._template_classic
        
        # Générer le HTML selon le type de voyage
        if template_type == 'day_trip':
            return self._render_day_trip(trip_data, render_method)
        else:
            return self._render_standard_trip(trip_data, render_method)
    
    def _render_standard_trip(self, trip_data: Dict[str, Any], render_method) -> str:
        """
        Génère une fiche pour un séjour standard
        
        Args:
            trip_data: Données du voyage
            render_method: Méthode de rendu selon le style
            
        Returns:
            HTML de la fiche
        """
        form_data = trip_data.get('form_data', {})
        api_data = trip_data.get('api_data', {})
        
        # Préparer les données pour le template
        context = {
            'agency': self.agency_config,
            'trip': {
                'destination': form_data.get('destination', ''),
                'hotel_name': form_data.get('hotel_name', ''),
                'dates': {
                    'start': form_data.get('date_start', ''),
                    'end': form_data.get('date_end', ''),
                    'duration': form_data.get('estimated_duration', 0)
                },
                'transport': form_data.get('transport_type', ''),
                'meal_plan': form_data.get('meal_plan', ''),
                'stars': form_data.get('stars', 3),
                'price': form_data.get('pack_price', 0),
                'num_people': form_data.get('num_people', 2),
                'activities': form_data.get('activities', [])
            },
            'enriched': {
                'photos': api_data.get('photos', []),
                'videos': api_data.get('videos', []),
                'attractions': api_data.get('attractions', {}).get('nearby', []),
                'reviews': api_data.get('reviews_summary', {}),
                'destination_info': api_data.get('destination_info', {}),
                'hotel_info': api_data.get('hotel_info', {})
            },
            'pricing': {
                'margin': trip_data.get('margin', 0),
                'savings': trip_data.get('savings', 0)
            }
        }
        
        return render_method(context, 'standard')
    
    def _render_day_trip(self, trip_data: Dict[str, Any], render_method) -> str:
        """
        Génère une fiche pour une excursion d'un jour
        
        Args:
            trip_data: Données du voyage
            render_method: Méthode de rendu selon le style
            
        Returns:
            HTML de la fiche
        """
        form_data = trip_data.get('form_data', {})
        api_data = trip_data.get('api_data', {})
        
        # Préparer les données pour le template
        context = {
            'agency': self.agency_config,
            'trip': {
                'destination': form_data.get('destination', ''),
                'departure_time': form_data.get('departure_time', '08:00'),
                'return_time': form_data.get('return_time', '20:00'),
                'departure_address': form_data.get('bus_departure_address', ''),
                'transport': 'autocar',  # Toujours autocar pour excursion
                'price': form_data.get('pack_price', 0),
                'activities': form_data.get('activities', []),
                'program': form_data.get('program', [])
            },
            'enriched': {
                'photos': api_data.get('photos', []),
                'videos': api_data.get('videos', []),
                'attractions': api_data.get('attractions', {}).get('nearby', []),
                'destination_info': api_data.get('destination_info', {})
            },
            'pricing': {
                'margin': trip_data.get('margin', 0),
                'savings': trip_data.get('savings', 0)
            }
        }
        
        return render_method(context, 'day_trip')
    
    def _template_classic(self, context: Dict[str, Any], trip_type: str) -> str:
        """
        Template Classic - Style traditionnel et épuré
        
        Args:
            context: Contexte avec toutes les données
            trip_type: Type de voyage
            
        Returns:
            HTML complet
        """
        
        # CSS du template classic
        css = f"""
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Georgia', serif;
                line-height: 1.6;
                color: #333;
                background: #fff;
            }}
            
            .header {{
                background: linear-gradient(135deg, {self.primary_color}, {self._darken_color(self.primary_color)});
                color: white;
                padding: 3rem 2rem;
                text-align: center;
            }}
            
            .header h1 {{
                font-size: 2.5rem;
                margin-bottom: 0.5rem;
            }}
            
            .header .subtitle {{
                font-size: 1.2rem;
                opacity: 0.9;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
            }}
            
            .section {{
                margin-bottom: 3rem;
                padding: 2rem;
                background: #f8f9fa;
                border-radius: 10px;
            }}
            
            .section h2 {{
                color: {self.primary_color};
                margin-bottom: 1.5rem;
                font-size: 1.8rem;
                border-bottom: 2px solid {self.primary_color};
                padding-bottom: 0.5rem;
            }}
            
            .photos-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
                margin-top: 2rem;
            }}
            
            .photo-card img {{
                width: 100%;
                height: 250px;
                object-fit: cover;
                border-radius: 10px;
            }}
            
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 2rem;
                margin-top: 2rem;
            }}
            
            .info-item {{
                background: white;
                padding: 1.5rem;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            
            .info-item .label {{
                font-weight: bold;
                color: #666;
                margin-bottom: 0.5rem;
            }}
            
            .info-item .value {{
                font-size: 1.1rem;
                color: #333;
            }}
            
            .price-box {{
                background: {self.primary_color};
                color: white;
                padding: 2rem;
                border-radius: 10px;
                text-align: center;
                margin: 2rem 0;
            }}
            
            .price-box .amount {{
                font-size: 3rem;
                font-weight: bold;
            }}
            
            .price-box .per-person {{
                font-size: 1rem;
                opacity: 0.9;
            }}
            
            .attractions {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
            }}
            
            .attraction-card {{
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            
            .attraction-card img {{
                width: 100%;
                height: 150px;
                object-fit: cover;
            }}
            
            .attraction-card .content {{
                padding: 1rem;
            }}
            
            .attraction-card .name {{
                font-weight: bold;
                margin-bottom: 0.5rem;
            }}
            
            .attraction-card .rating {{
                color: #f59e0b;
            }}
            
            .program-timeline {{
                position: relative;
                padding-left: 3rem;
            }}
            
            .program-item {{
                position: relative;
                padding-bottom: 2rem;
            }}
            
            .program-item::before {{
                content: '';
                position: absolute;
                left: -2rem;
                top: 0;
                width: 12px;
                height: 12px;
                background: {self.primary_color};
                border-radius: 50%;
            }}
            
            .program-item::after {{
                content: '';
                position: absolute;
                left: -1.94rem;
                top: 12px;
                width: 2px;
                height: calc(100% - 12px);
                background: #ddd;
            }}
            
            .program-item:last-child::after {{
                display: none;
            }}
            
            .program-time {{
                font-weight: bold;
                color: {self.primary_color};
                margin-bottom: 0.5rem;
            }}
            
            .footer {{
                background: #333;
                color: white;
                padding: 2rem;
                text-align: center;
                margin-top: 3rem;
            }}
            
            .footer .contact {{
                margin-top: 1rem;
            }}
            
            .footer .contact a {{
                color: white;
                text-decoration: none;
                margin: 0 1rem;
            }}
            
            @media print {{
                .section {{
                    break-inside: avoid;
                }}
            }}
        """
        
        # Générer le contenu selon le type
        if trip_type == 'day_trip':
            content = self._generate_day_trip_content(context)
        else:
            content = self._generate_standard_content(context)
        
        # HTML complet
        html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{context['trip']['destination']} - {self.agency_name}</title>
    <style>{css}</style>
</head>
<body>
    {content}
</body>
</html>
"""
        
        return html
    
    def _generate_standard_content(self, context: Dict[str, Any]) -> str:
        """
        Génère le contenu HTML pour un séjour standard
        
        Args:
            context: Contexte avec les données
            
        Returns:
            HTML du contenu
        """
        trip = context['trip']
        enriched = context['enriched']
        
        # Photos
        photos_html = ""
        if enriched['photos']:
            photos_html = f"""
            <section class="section">
                <h2>📸 Photos</h2>
                <div class="photos-grid">
                    {' '.join([f'<div class="photo-card"><img src="{p["url"]}" alt="Photo"></div>' for p in enriched['photos'][:6]])}
                </div>
            </section>
            """
        
        # Attractions
        # MODIFIÉ : Correction de la source des attractions
        attractions_html = ""
        if enriched.get('attractions'):
            attractions_items = ""
            for att in enriched['attractions']:
                img_html = f'<img src="{att["photo_url"]}" alt="{att["name"]}">' if att.get('photo_url') else '<div style="height:150px;background:#ddd;"></div>'
                attractions_items += f"""
                <div class="attraction-card">
                    {img_html}
                    <div class="content">
                        <div class="name">{att['name']}</div>
                        <div class="rating">{'⭐ ' + str(att.get('rating', '')) if att.get('rating') else ''}</div>
                    </div>
                </div>
                """
            
            attractions_html = f"""
            <section class="section">
                <h2>🎯 Attractions à proximité</h2>
                <div class="attractions">
                    {attractions_items}
                </div>
            </section>
            """
        
        # Contenu complet
        content = f"""
        <header class="header">
            <h1>{trip['destination']}</h1>
            <div class="subtitle">{trip.get('hotel_name', 'Séjour découverte')}</div>
        </header>
        
        <div class="container">
            <!-- Informations principales -->
            <section class="section">
                <h2>📋 Informations du séjour</h2>
                <div class="info-grid">
                    <div class="info-item">
                        <div class="label">📅 Dates</div>
                        <div class="value">{trip['dates']['start']} au {trip['dates']['end']}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">✈️ Transport</div>
                        <div class="value">{self._format_transport(trip['transport'])}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">🏨 Hébergement</div>
                        <div class="value">{'⭐' * trip.get('stars', 3)} {trip.get('hotel_name', 'Hôtel')}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">🍽️ Formule</div>
                        <div class="value">{self._format_meal_plan(trip.get('meal_plan', ''))}</div>
                    </div>
                </div>
            </section>
            
            <!-- Prix -->
            <div class="price-box">
                <div class="amount">{trip['price']} €</div>
                <div class="per-person">par personne</div>
            </div>
            
            {photos_html}
            
            {attractions_html}
            
            <!-- Contact -->
            <footer class="footer">
                <h3>{self.agency_name}</h3>
                <div class="contact">
                    <a href="mailto:{self.contact_email}">✉️ {self.contact_email}</a>
                    <a href="tel:{self.contact_phone}">📞 {self.contact_phone}</a>
                </div>
            </footer>
        </div>
        """
        
        return content
    
    def _generate_day_trip_content(self, context: Dict[str, Any]) -> str:
        """
        Génère le contenu HTML pour une excursion d'un jour
        
        Args:
            context: Contexte avec les données
            
        Returns:
            HTML du contenu
        """
        trip = context['trip']
        enriched = context['enriched']
        
        # Programme de la journée
        program_html = ""
        if trip.get('program'):
            program_items = ""
            for item in trip['program']:
                program_items += f"""
                <div class="program-item">
                    <div class="program-time">{item.get('time', '')}</div>
                    <div class="program-activity">{item.get('activity', '')}</div>
                </div>
                """
            
            program_html = f"""
            <section class="section">
                <h2>📅 Programme de la journée</h2>
                <div class="program-timeline">
                    {program_items}
                </div>
            </section>
            """
        
        # Contenu complet
        content = f"""
        <header class="header">
            <h1>Excursion à {trip['destination']}</h1>
            <div class="subtitle">Voyage d'un jour en autocar</div>
        </header>
        
        <div class="container">
            <!-- Informations principales -->
            <section class="section">
                <h2>📋 Informations pratiques</h2>
                <div class="info-grid">
                    <div class="info-item">
                        <div class="label">🚌 Départ</div>
                        <div class="value">{trip['departure_time']} - {trip.get('departure_address', 'À définir')}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">🏁 Retour</div>
                        <div class="value">{trip['return_time']}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">📍 Destination</div>
                        <div class="value">{trip['destination']}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">🎯 Activités</div>
                        <div class="value">{', '.join(trip.get('activities', []))}</div>
                    </div>
                </div>
            </section>
            
            <!-- Prix -->
            <div class="price-box">
                <div class="amount">{trip['price']} €</div>
                <div class="per-person">tout compris</div>
            </div>
            
            {program_html}
            
            <!-- Contact -->
            <footer class="footer">
                <h3>{self.agency_name}</h3>
                <div class="contact">
                    <a href="mailto:{self.contact_email}">✉️ {self.contact_email}</a>
                    <a href="tel:{self.contact_phone}">📞 {self.contact_phone}</a>
                </div>
            </footer>
        </div>
        """
        
        return content
    
    def _template_modern(self, context: Dict[str, Any], trip_type: str) -> str:
        """
        Template Modern - Style contemporain avec animations
        À implémenter : design plus moderne avec gradients et animations CSS
        """
        # Pour l'instant, utilise le template classic
        return self._template_classic(context, trip_type)
    
    def _template_luxury(self, context: Dict[str, Any], trip_type: str) -> str:
        """
        Template Luxury - Style premium et élégant
        À implémenter : design luxueux avec effets visuels sophistiqués
        """
        # Pour l'instant, utilise le template classic
        return self._template_classic(context, trip_type)
    
    # ==============================================================================
    # UTILITAIRES
    # ==============================================================================
    
    def _format_transport(self, transport: str) -> str:
        """Formate le type de transport"""
        transports = {
            'avion': '✈️ Avion',
            'train': '🚂 Train',
            'autocar': '🚌 Autocar',
            'voiture': '🚗 Voiture'
        }
        return transports.get(transport, transport.capitalize())
    
    def _format_meal_plan(self, meal_plan: str) -> str:
        """Formate la formule repas"""
        plans = {
            'logement_seul': 'Logement seul',
            'petit_dejeuner': 'Petit-déjeuner',
            'demi_pension': 'Demi-pension',
            'pension_complete': 'Pension complète',
            'all_in': 'All Inclusive'
        }
        return plans.get(meal_plan, meal_plan.replace('_', ' ').capitalize())
    
    def _darken_color(self, hex_color: str, factor: float = 0.8) -> str:
        """
        Assombrit une couleur hexadécimale
        
        Args:
            hex_color: Couleur au format #RRGGBB
            factor: Facteur d'assombrissement (0-1)
            
        Returns:
            Couleur assombrie
        """
        try:
            # Enlever le #
            hex_color = hex_color.lstrip('#')
            
            # Convertir en RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # Assombrir
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)
            
            # Reconvertir en hex
            return f'#{r:02x}{g:02x}{b:02x}'
            
        except:
            return '#2563eb'  # Couleur par défaut si erreur


# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================

def render_trip_template(data: Dict[str, Any], 
                        template_type: str,
                        agency_style: str,
                        agency_config: Dict[str, Any]) -> str:
    """
    Point d'entrée pour générer une fiche de voyage
    
    Args:
        data: Données complètes du voyage
        template_type: 'standard' ou 'day_trip'
        agency_style: 'classic', 'modern' ou 'luxury'
        agency_config: Configuration de l'agence
        
    Returns:
        HTML complet de la fiche
    """
    engine = TemplateEngine(agency_config)
    return engine.render_trip_template(data, template_type, agency_style)


# ==============================================================================
# TESTS
# ==============================================================================

def _run_tests():
    """
    Tests du Template Engine
    Lancez : python services/template_engine.py
    """
    
    print("\n" + "="*60)
    print("TEST TEMPLATE ENGINE")
    print("="*60)
    
    # Configuration d'agence de test
    test_agency_config = {
        'name': 'Voyages Privilèges',
        'primary_color': '#3B82F6',
        'logo_url': 'https://example.com/logo.png',
        'contact_email': 'contact@voyages-privileges.be',
        'contact_phone': '+32 488 43 33 44'
    }
    
    # Données de voyage de test
    test_trip_data = {
        'form_data': {
            'destination': 'Rome, Italie',
            'hotel_name': 'Hotel Colosseo',
            'date_start': '2025-03-15',
            'date_end': '2025-03-18',
            'duration': 3,
            'transport_type': 'avion',
            'meal_plan': 'demi_pension',
            'stars': 4,
            'pack_price': 500,
            'num_people': 2,
            'activities': ['Colisée', 'Vatican', 'Fontaine de Trevi']
        },
        'api_data': {
            'photos': [
                {'url': 'https://via.placeholder.com/800x600?text=Rome+1'},
                {'url': 'https://via.placeholder.com/800x600?text=Rome+2'},
                {'url': 'https://via.placeholder.com/800x600?text=Rome+3'}
            ],
            'attractions': [
                {
                    'name': 'Colisée',
                    'rating': 4.7,
                    'photo_url': 'https://via.placeholder.com/400x300?text=Colosseum'
                },
                {
                    'name': 'Vatican',
                    'rating': 4.8,
                    'photo_url': 'https://via.placeholder.com/400x300?text=Vatican'
                }
            ]
        },
        'margin': 150,
        'savings': 100
    }
    
    # Test génération template classic
    print("\n📄 Génération d'une fiche Classic...")
    html = render_trip_template(
        test_trip_data,
        'standard',
        'classic',
        test_agency_config
    )
    
    # Sauvegarder le HTML pour test
    output_file = 'test_fiche_voyage.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Fiche générée ! Sauvegardée dans {output_file}")
    print(f"   - Taille: {len(html)} caractères")
    print(f"   - Style: Classic")
    print(f"   - Type: Séjour standard")
    
    # Test excursion d'un jour
    test_day_trip = {
        'form_data': {
            'destination': 'Bruges',
            'departure_time': '08:00',
            'return_time': '20:00',
            'departure_address': 'Place de la Gare, Bruxelles',
            'pack_price': 75,
            'activities': ['Centre historique', 'Canaux', 'Béguinage'],
            'program': [
                {'time': '08:00', 'activity': 'Départ de Bruxelles'},
                {'time': '10:00', 'activity': 'Arrivée à Bruges'},
                {'time': '10:30', 'activity': 'Visite guidée du centre historique'},
                {'time': '12:30', 'activity': 'Déjeuner libre'},
                {'time': '14:00', 'activity': 'Balade en bateau sur les canaux'},
                {'time': '16:00', 'activity': 'Temps libre'},
                {'time': '18:00', 'activity': 'Départ retour'},
                {'time': '20:00', 'activity': 'Arrivée à Bruxelles'}
            ]
        },
        'api_data': {},
        'margin': 30,
        'savings': 20
    }
    
    print("\n📄 Génération d'une fiche Excursion...")
    html_day = render_trip_template(
        test_day_trip,
        'day_trip',
        'classic',
        test_agency_config
    )
    
    output_file_day = 'test_excursion_bruges.html'
    with open(output_file_day, 'w', encoding='utf-8') as f:
        f.write(html_day)
    
    print(f"✅ Fiche excursion générée ! Sauvegardée dans {output_file_day}")
    
    print("\n✅ Tests terminés ! Ouvrez les fichiers HTML dans votre navigateur pour voir le résultat.")

if __name__ == "__main__":
    _run_tests()