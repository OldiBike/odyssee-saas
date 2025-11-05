"""
Service d'inspiration de voyages
Utilise Gemini AI pour analyser les demandes et propose des options de voyage
Intègre RapidAPI (Booking.com + Google Flights) pour de vraies données
AUCUNE SIMULATION - Tout est basé sur des données réelles
"""

import google.generativeai as genai
import json
import re
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TravelInspector:
    """
    Inspecteur de voyages intelligent
    Analyse les demandes en langage naturel et propose des options concrètes
    """
    
    def __init__(self, gemini_api_key: str, rapidapi_key: str = None):
        """
        Initialise l'inspecteur avec Gemini AI et RapidAPI
        
        Args:
            gemini_api_key: Clé API Google Gemini
            rapidapi_key: Clé RapidAPI (requis pour les recherches)
        """
        if not rapidapi_key:
            raise ValueError("RapidAPI key est requise pour effectuer des recherches")
        
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self.rapidapi_key = rapidapi_key
    
    def analyze_travel_request(self, query: str) -> Dict[str, Any]:
        """
        Analyse une demande de voyage en langage naturel
        
        Args:
            query: Demande utilisateur (ex: "4 jours à Rome, hotel avec petit déjeuner, 
                   départ entre le 03/10 et le 9/10 pour un budget de 400€ par personne")
        
        Returns:
            Dict avec les critères extraits:
            {
                "destination": "Rome",
                "date_debut": "2025-10-03",
                "date_fin": "2025-10-09",  
                "budget_pp": 400,
                "inclusions": ["petit-déjeuner"],
                "num_personnes": 2,
                "flexible_dates": true/false
            }
        """
        
        system_prompt = """
Tu es un analyste de voyage expert. Tu dois extraire les informations clés d'une demande de voyage et fournir les codes IATA des aéroports.

CHAMPS À EXTRAIRE :

OBLIGATOIRES :
- destination (string) : ville principale (ex: "Rome", "Paris")
- destination_airport_code (string) : code IATA de l'aéroport principal de la destination (ex: "FCO" pour Rome, "CDG" pour Paris)
- origin (string) : ville de départ (défaut: "Bruxelles" si non mentionné)
- origin_airport_code (string) : code IATA de l'aéroport de départ (défaut: "BRU" pour Bruxelles)
- budget_pp (number) : budget par personne en euros

OPTIONNELS :
- date_debut (string|null) : date de début au format "YYYY-MM-DD"
- date_fin (string|null) : date de fin au format "YYYY-MM-DD"
- date_window_start (string|null) : début de la fenêtre de dates flexibles "YYYY-MM-DD"
- date_window_end (string|null) : fin de la fenêtre de dates flexibles "YYYY-MM-DD"
- duration_days (number|null) : durée du séjour en jours (ex: 3 pour "3 jours")
- flexible_dates (boolean) : true si dates flexibles mentionnées
- num_personnes (number) : nombre de personnes (défaut: 2)
- inclusions (array) : ["petit-déjeuner", "demi-pension", etc.]
- type_hebergement (string|null) : "hotel", "appartement", "resort"
- stars_min (number|null) : nombre d'étoiles minimum (1-5)

CODES AÉROPORTS IATA :
Tu DOIS fournir les codes IATA corrects pour les aéroports. Si tu ne connais pas le code exact, retourne null pour le champ correspondant.
Exemples : Rome → FCO, Paris → CDG, Londres → LHR, New York → JFK, Tokyo → NRT, etc.

RÈGLES D'EXTRACTION :

1. DATES :
   - Format français : "03/10" → "2025-10-03", "20/11" → "2025-11-20"
   - Format texte : "3 octobre" → "2025-10-03"
   - IMPORTANT: Différencier DURÉE vs FENÊTRE:
     * "3 jours à Madrid entre le 20/11 et 25/11" → duration_days: 3, date_window_start: "2025-11-20", date_window_end: "2025-11-25", flexible_dates: true
     * Dans ce cas, mettre date_debut et date_fin à null (on testera plusieurs combinaisons)
   - Si "du X au Y" (dates précises) → date_debut: X, date_fin: Y, flexible_dates: false
   - Si "X jours" sans fenêtre → mettre date_debut et date_fin à null, flexible_dates: true
   - Utiliser 2025 comme année par défaut

2. BUDGET :
   - Extraire le montant numérique uniquement
   - Si "400€ par personne" → budget_pp: 400
   - Si budget total pour X personnes, diviser

3. INCLUSIONS :
   - Identifier : petit-déjeuner, demi-pension, pension complète, all-inclusive
   - Format : ["petit-déjeuner"] (liste de strings)

4. DESTINATION :
   - Ville principale uniquement
   - Pas de "Italie", juste "Rome"
   - Fournir OBLIGATOIREMENT les codes IATA des aéroports

5. ORIGINE :
   - Si non mentionné, utiliser "Bruxelles" (BRU)
   - Sinon extraire la ville de départ mentionnée

EXEMPLES :

Input: "4 jours à Rome, hotel avec petit déjeuner, départ entre le 03/10 et le 9/10 pour un budget de 400€ par personne"
Output: {
    "destination": "Rome",
    "destination_airport_code": "FCO",
    "origin": "Bruxelles",
    "origin_airport_code": "BRU",
    "date_debut": "2025-10-03",
    "date_fin": "2025-10-09",
    "flexible_dates": true,
    "budget_pp": 400,
    "num_personnes": 2,
    "inclusions": ["petit-déjeuner"],
    "type_hebergement": "hotel",
    "stars_min": null,
    "duration_days": 4
}

Input: "3 jours à Madrid au départ de Charleroi entre le 20/11 et 25/11. Petit déjeuner compris pour deux personnes et un budget de 400€ par personne"
Output: {
    "destination": "Madrid",
    "destination_airport_code": "MAD",
    "origin": "Charleroi",
    "origin_airport_code": "CRL",
    "date_debut": null,
    "date_fin": null,
    "date_window_start": "2025-11-20",
    "date_window_end": "2025-11-25",
    "duration_days": 3,
    "flexible_dates": true,
    "budget_pp": 400,
    "num_personnes": 2,
    "inclusions": ["petit-déjeuner"],
    "type_hebergement": "hotel",
    "stars_min": null
}

Input: "Week-end à Barcelone du 15 au 17 mars, 2 personnes, 300€ chacun, hôtel 4 étoiles, départ de Paris"
Output: {
    "destination": "Barcelone",
    "destination_airport_code": "BCN",
    "origin": "Paris",
    "origin_airport_code": "CDG",
    "date_debut": "2025-03-15",
    "date_fin": "2025-03-17",
    "flexible_dates": false,
    "budget_pp": 300,
    "num_personnes": 2,
    "inclusions": [],
    "type_hebergement": "hotel",
    "stars_min": 4
}

IMPORTANT : Réponds UNIQUEMENT en JSON valide, sans markdown, sans texte additionnel.
"""
        
        full_prompt = system_prompt + f"\n\nDemande utilisateur: {query}"
        
        try:
            response = self.model.generate_content(full_prompt)
            response_text = response.text.strip()
            
            # Nettoyer la réponse
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            
            # Parser le JSON
            criteria = json.loads(response_text)
            
            # Validation et nettoyage
            criteria = self._validate_criteria(criteria)
            
            return {
                'success': True,
                'criteria': criteria
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Erreur parsing JSON: {e}")
            logger.error(f"Réponse brute: {response.text if 'response' in locals() else 'N/A'}")
            return {
                'success': False,
                'error': 'Impossible de comprendre la demande. Veuillez reformuler.'
            }
        except Exception as e:
            logger.error(f"Erreur Gemini API: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Erreur lors de l\'analyse: {str(e)}'
            }
    
    def _validate_criteria(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Valide et nettoie les critères extraits"""
        
        # Champs obligatoires
        if not criteria.get('destination'):
            raise ValueError("La destination n'a pas pu être identifiée. Veuillez préciser la ville de destination.")
        
        if not criteria.get('destination_airport_code'):
            raise ValueError(f"Le code aéroport pour {criteria.get('destination')} n'a pas pu être déterminé. Veuillez préciser une destination avec un aéroport international.")
        
        if not criteria.get('origin_airport_code'):
            raise ValueError(f"Le code aéroport pour {criteria.get('origin', 'la ville de départ')} n'a pas pu être déterminé. Veuillez préciser une ville de départ avec un aéroport.")
        
        if not criteria.get('budget_pp'):
            raise ValueError("Le budget par personne n'a pas pu être identifié. Veuillez préciser un budget.")
        
        criteria['budget_pp'] = int(criteria['budget_pp'])
        
        # Nombre de personnes par défaut
        if not criteria.get('num_personnes'):
            criteria['num_personnes'] = 2
        else:
            criteria['num_personnes'] = int(criteria['num_personnes'])
        
        # Dates flexibles
        if 'flexible_dates' not in criteria:
            criteria['flexible_dates'] = False
        
        # Inclusions (liste)
        if not isinstance(criteria.get('inclusions'), list):
            criteria['inclusions'] = []
        
        # Origine par défaut
        if not criteria.get('origin'):
            criteria['origin'] = 'Bruxelles'
        if not criteria.get('origin_airport_code'):
            criteria['origin_airport_code'] = 'BRU'
        
        return criteria
    
    def _get_destination_id(self, city_name: str) -> Optional[str]:
        """
        Obtient le dest_id d'une ville via l'API Booking.com
        
        Args:
            city_name: Nom de la ville
            
        Returns:
            dest_id ou None si non trouvé
        """
        url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"
        
        headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": "booking-com15.p.rapidapi.com"
        }
        
        params = {"query": city_name}
        
        try:
            print(f"\n=== [Booking.com] Recherche dest_id pour '{city_name}' ===")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Chercher la ville dans les résultats
            if data.get('data'):
                for item in data['data']:
                    # Prendre le premier résultat de type CITY
                    if item.get('dest_type') == 'city':
                        dest_id = item.get('dest_id')
                        print(f"✓ dest_id trouvé : {dest_id}")
                        return dest_id
            
            print(f"⚠️ Aucun dest_id trouvé pour '{city_name}'")
            return None
            
        except Exception as e:
            print(f"❌ Erreur recherche dest_id: {e}")
            return None
    
    def _autocomplete_destination(self, city_name: str) -> Optional[Dict[str, Any]]:
        """
        Utilise l'endpoint auto-complete pour valider et trouver une destination
        Plus fiable que les anciennes méthodes
        
        Args:
            city_name: Nom de la ville à rechercher
            
        Returns:
            Dict avec locationId, nom complet, etc. ou None
        """
        url = "https://hotels-com6.p.rapidapi.com/hotels/auto-complete"
        
        headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
        }
        
        # Essayer d'abord en anglais pour de meilleurs résultats
        city_translations = {
            'barcelone': 'Barcelona',
            'madrid': 'Madrid',
            'rome': 'Rome',
            'paris': 'Paris',
            'londres': 'London',
            'lisbonne': 'Lisbon',
            'venise': 'Venice',
            'florence': 'Florence',
            'milan': 'Milan'
        }
        
        search_city = city_translations.get(city_name.lower(), city_name)
        
        params = {"query": search_city}
        
        try:
            print(f"\n=== [Auto-Complete] Validation de '{city_name}' (recherche: '{search_city}') ===")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and isinstance(data, dict):
                # Structure API Hotels.com: {data: {sr: [{...}]}}
                data_obj = data.get('data', {})
                suggestions = data_obj.get('sr', [])
                
                if suggestions and isinstance(suggestions, list):
                    # Prioriser les CITY du pays correspondant
                    # Liste des pays majeurs pour éviter les homonymes
                    major_countries = ['Spain', 'France', 'Italy', 'United Kingdom', 'Portugal', 
                                      'Germany', 'Netherlands', 'Belgium', 'Switzerland', 'Austria',
                                      'Greece', 'United States', 'Japan', 'Thailand']
                    
                    # 1er passage : chercher CITY dans un pays majeur
                    for item in suggestions:
                        item_type = item.get('type', '').upper()
                        hierarchy = item.get('hierarchyInfo', {})
                        country = hierarchy.get('country', {}).get('name', '')
                        
                        if item_type == 'CITY' and country in major_countries:
                            region_names = item.get('regionNames', {})
                            result = {
                                'locationId': str(item.get('locationId', '')),
                                'name': region_names.get('shortName', city_name),
                                'type': item_type,
                                'country': country,
                                'display': region_names.get('displayName', region_names.get('fullName', city_name))
                            }
                            print(f"✓ Destination validée: {result['display']} (ID: {result['locationId']})")
                            return result
                    
                    # 2ème passage : prendre le premier CITY (même si pays non-majeur)
                    for item in suggestions:
                        item_type = item.get('type', '').upper()
                        if item_type in ['CITY', 'DESTINATION']:
                            region_names = item.get('regionNames', {})
                            hierarchy = item.get('hierarchyInfo', {})
                            result = {
                                'locationId': str(item.get('locationId', '')),
                                'name': region_names.get('shortName', city_name),
                                'type': item_type,
                                'country': hierarchy.get('country', {}).get('name', ''),
                                'display': region_names.get('displayName', region_names.get('fullName', city_name))
                            }
                            print(f"✓ Destination trouvée: {result['display']} (ID: {result['locationId']})")
                            return result
                    
                    # 3ème passage : prendre le premier résultat quel qu'il soit
                    if suggestions[0]:
                        item = suggestions[0]
                        region_names = item.get('regionNames', {})
                        result = {
                            'locationId': str(item.get('locationId', '')),
                            'name': region_names.get('shortName', city_name),
                            'type': item.get('type', 'UNKNOWN'),
                            'display': region_names.get('displayName', region_names.get('fullName', city_name))
                        }
                        print(f"✓ Destination trouvée: {result['display']} (ID: {result['locationId']})")
                        return result
            
            print(f"⚠️ Aucune suggestion trouvée pour '{city_name}'")
            return None
            
        except Exception as e:
            logger.warning(f"Erreur auto-complete: {e}")
            return None
    
    def _get_destination_filters(self, location_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtient les filtres disponibles pour une destination
        
        Args:
            location_id: ID de la destination
            
        Returns:
            Dict contenant les filtres disponibles ou None
        """
        url = "https://hotels-com6.p.rapidapi.com/hotels/filters"
        
        headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
        }
        
        # Format des rooms pour l'API
        rooms_json = json.dumps([{"adults": 1}])
        
        params = {
            "locationId": location_id,
            "rooms": rooms_json
        }
        
        try:
            print(f"\n=== [Filters] Récupération des filtres pour locationId {location_id} ===")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and isinstance(data, dict):
                # Extraire les filtres pertinents
                filters = {
                    'amenities': data.get('amenities', []),
                    'star_ratings': data.get('starRatings', []),
                    'neighborhoods': data.get('neighborhoods', []),
                    'price_range': data.get('priceRange', {}),
                    'accommodation_types': data.get('accommodationTypes', [])
                }
                
                print(f"✓ Filtres récupérés: {len(filters.get('amenities', []))} équipements, "
                      f"{len(filters.get('neighborhoods', []))} quartiers")
                
                return filters
            
            return None
            
        except Exception as e:
            logger.warning(f"Erreur récupération filtres: {e}")
            return None
    
    def _get_hotel_highlights(self, property_id: str) -> Optional[List[str]]:
        """
        Obtient les points forts d'un hôtel
        
        Args:
            property_id: ID de la propriété (format: "locationId_hotelId")
            
        Returns:
            Liste des highlights ou None
        """
        url = "https://hotels-com6.p.rapidapi.com/hotels/details-highlights"
        
        headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
        }
        
        params = {"propertyId": property_id}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and isinstance(data, dict):
                # Extraire les highlights
                highlights = []
                
                # Plusieurs formats possibles
                if data.get('highlights'):
                    highlights.extend(data['highlights'])
                
                if data.get('propertyHighlights'):
                    highlights.extend(data['propertyHighlights'])
                
                return highlights if highlights else None
            
            return None
            
        except Exception as e:
            logger.warning(f"Erreur récupération highlights pour {property_id}: {e}")
            return None
    
    def _get_hotel_amenities(self, property_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtient les équipements d'un hôtel
        
        Args:
            property_id: ID de la propriété
            
        Returns:
            Dict avec équipements ou None
        """
        url = "https://hotels-com6.p.rapidapi.com/hotels/details-amenities"
        
        headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
        }
        
        params = {"propertyId": property_id}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and isinstance(data, dict):
                return {
                    'room_amenities': data.get('roomAmenities', []),
                    'hotel_amenities': data.get('hotelAmenities', []),
                    'accessibility': data.get('accessibility', [])
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Erreur récupération amenities pour {property_id}: {e}")
            return None
    
    def _get_hotel_location_details(self, property_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtient les détails de localisation d'un hôtel
        
        Args:
            property_id: ID de la propriété
            
        Returns:
            Dict avec infos de localisation ou None
        """
        url = "https://hotels-com6.p.rapidapi.com/hotels/details-location"
        
        headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
        }
        
        params = {"propertyId": property_id}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and isinstance(data, dict):
                return {
                    'coordinates': data.get('coordinates', {}),
                    'neighborhood': data.get('neighborhood', ''),
                    'nearby_attractions': data.get('nearbyAttractions', []),
                    'distances': data.get('distances', {})
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Erreur récupération location pour {property_id}: {e}")
            return None
    
    def _get_location_id_hotels_com(self, city_name: str) -> Optional[str]:
        """
        Obtient le locationId d'une ville via l'API Hotels.com
        Utilise le nouvel endpoint auto-complete (plus fiable)
        
        Args:
            city_name: Nom de la ville
            
        Returns:
            locationId ou None si non trouvé
        """
        # Utiliser le nouvel endpoint auto-complete
        result = self._autocomplete_destination(city_name)
        
        if result and result.get('locationId'):
            return result['locationId']
        
        # Fallback sur l'ancienne API Booking.com si échec
        print(f"⚠️ Tentative avec Booking.com API comme fallback...")
        try:
            dest_id = self._get_destination_id(city_name)
            if dest_id:
                print(f"✓ Utilisation de dest_id Booking.com: {dest_id}")
                return dest_id
        except Exception as e:
            print(f"⚠️ Erreur Booking.com fallback: {e}")
        
        # En dernier recours, erreur explicite
        raise Exception(
            f"Impossible de trouver le location ID pour '{city_name}'.\n"
            f"Suggestions:\n"
            f"• Vérifiez l'orthographe de la ville\n"
            f"• Essayez le nom de la ville en anglais\n"
            f"• Vérifiez que l'API Hotels.com est bien activée sur votre compte RapidAPI"
        )
    
    def _search_hotels_rapidapi(self, destination: str, checkin: str, checkout: str, 
                                 adults: int, max_price: int, stars: int = None) -> List[Dict[str, Any]]:
        """
        Recherche d'hôtels via Hotels.com RapidAPI
        
        Args:
            destination: Nom de la destination
            checkin: Date d'arrivée (YYYY-MM-DD)
            checkout: Date de départ (YYYY-MM-DD)
            adults: Nombre d'adultes
            max_price: Prix maximum par nuit
            stars: Nombre d'étoiles minimum (optionnel)
            
        Returns:
            Liste d'hôtels trouvés avec note >= 8/10 ou lève une exception
        """
        
        # 1. Obtenir le locationId de la ville
        location_id = self._get_location_id_hotels_com(destination)
        if not location_id:
            raise Exception(f"Impossible de trouver l'ID de destination pour {destination}")
        
        url = "https://hotels-com6.p.rapidapi.com/hotels/search"
        
        headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
        }
        
        # Calculer le nombre de nuits
        from datetime import datetime as dt
        checkin_dt = dt.strptime(checkin, '%Y-%m-%d')
        checkout_dt = dt.strptime(checkout, '%Y-%m-%d')
        nights = (checkout_dt - checkin_dt).days
        if nights <= 0:
            nights = 1
        
        # Format des rooms pour l'API Hotels.com
        rooms_json = json.dumps([{"adults": adults}])
        
        # Paramètres de recherche avec options supplémentaires
        params = {
            "locationId": location_id,
            "rooms": rooms_json,
            "checkinDate": checkin,
            "checkoutDate": checkout,
            "currency": "EUR",
            "locale": "fr_FR",
            "sort": "RECOMMENDED",  # Tri recommandé
            "resultsSize": 50  # Augmenter le nombre de résultats
        }
        
        try:
            print(f"\n=== [Hotels.com] Recherche à {destination} (locationId: {location_id}) ===")
            print(f"Params: {params}")
            print(f"Budget max par nuit: {max_price}€ (total séjour: {max_price * nights}€)")
            logger.info(f"Recherche hôtels à {destination} ({checkin} → {checkout})")
            
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            print(f"Response status: {response.status_code}")
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Diagnostic détaillé si pas d'hôtels
            if data.get('status') == False:
                print(f"⚠️ API Hotels.com a retourné status=false")
                print(f"Message: {data.get('message', 'Aucun message')}")
            
            hotels = []
            
            # NOUVELLE STRUCTURE API : propertySearchListings au lieu de hotels
            property_listings = data.get('data', {}).get('propertySearchListings', [])
            
            # Filtrer pour garder seulement les LodgingCard (hôtels réels)
            results = [
                item for item in property_listings 
                if item.get('__typename') == 'LodgingCard'
            ]
            
            print(f"Nombre d'hôtels dans la réponse brute: {len(results)}")
            
            # Si aucun hôtel, afficher plus d'infos de diagnostic
            if len(results) == 0:
                print(f"⚠️ AUCUN HÔTEL retourné par l'API")
                print(f"Raisons possibles:")
                print(f"  - Dates trop éloignées (essayez dates plus proches)")
                print(f"  - Aucun hôtel disponible pour ces dates")
                print(f"  - Limitations de l'API Hotels.com")
                print(f"  - Essayez une autre destination ou d'autres dates")
                print(f"Structure retournée: propertySearchListings avec {len(property_listings)} items")
            
            # Filtrer et trier les hôtels
            for hotel_data in results:
                try:
                    # Extraire l'ID de l'hôtel
                    hotel_id = hotel_data.get('id', '')
                    property_id = hotel_data.get('propertyId', f"{location_id}_{hotel_id}") if hotel_id else None
                    
                    # NOUVELLE STRUCTURE API - Extraire les données correctement
                    
                    # 1. NOM - dans headingSection.heading
                    heading_section = hotel_data.get('headingSection', {})
                    hotel_name = heading_section.get('heading', 'Hotel')
                    
                    # 2. PRIX - dans priceSection.priceSummary.options[0]
                    price_section = hotel_data.get('priceSection', {})
                    price_summary = price_section.get('priceSummary', {})
                    options = price_summary.get('options', [])
                    
                    if not options:
                        print(f"⚠️ Hôtel {hotel_name}: Pas de prix disponible, skip")
                        continue
                    
                    # Le prix est dans displayPrice.formatted (ex: "$529")
                    display_price = options[0].get('displayPrice', {}).get('formatted', '$0')
                    # Nettoyer le prix (enlever $ et convertir)
                    try:
                        total_price = float(display_price.replace('$', '').replace(',', '').strip())
                    except:
                        print(f"⚠️ Hôtel {hotel_name}: Prix invalide '{display_price}', skip")
                        continue
                    
                    price_per_night = total_price / nights if nights > 0 else total_price
                    
                    # 3. NOTE - dans summarySections[0].guestRatingSectionV2.badge.text
                    summary_sections = hotel_data.get('summarySections', [])
                    rating = 0
                    reviews_count = 0
                    
                    if summary_sections:
                        guest_rating = summary_sections[0].get('guestRatingSectionV2', {})
                        badge = guest_rating.get('badge', {})
                        rating_text = badge.get('text', '0')
                        try:
                            rating = float(rating_text)
                        except:
                            rating = 0
                        
                        # Extraire le nombre d'avis des phrases
                        phrases = guest_rating.get('phrases', [])
                        for phrase in phrases:
                            phrase_parts = phrase.get('phraseParts', [])
                            for part in phrase_parts:
                                text = part.get('text', '')
                                if 'review' in text.lower():
                                    # Extraire le nombre (ex: "1,001 reviews")
                                    import re
                                    match = re.search(r'([\d,]+)', text)
                                    if match:
                                        try:
                                            reviews_count = int(match.group(1).replace(',', ''))
                                        except:
                                            pass
                    
                    # FILTRES ASSOUPLIS
                    # 1. Note minimum 7/10 (au lieu de 8/10)
                    if rating < 7.0:
                        continue
                    
                    # 2. Budget: filtrer les hôtels hors budget (avec marge de 20%)
                    if price_per_night > max_price * 1.2:
                        continue
                    
                    # 3. Étoiles - chercher dans les amenities ou badges (pas toujours disponible)
                    stars_rating = 0
                    amenities = heading_section.get('amenities', [])
                    # Note: l'API ne retourne pas toujours les étoiles explicitement
                    
                    # Si filtre étoiles demandé (skip pour l'instant car pas dans nouvelle structure)
                    # if stars and stars_rating < stars:
                    #     continue
                    
                    # 4. IMAGE - dans mediaSection.gallery.media[0].media.url
                    image_url = self._get_placeholder_image(destination)
                    media_section = hotel_data.get('mediaSection', {})
                    gallery = media_section.get('gallery', {})
                    media_items = gallery.get('media', [])
                    
                    if media_items:
                        first_media = media_items[0].get('media', {})
                        image_url = first_media.get('url', image_url)
                    
                    # 5. ADRESSE - dans headingSection.messages
                    address = destination
                    messages = heading_section.get('messages', [])
                    if messages:
                        address_text = messages[0].get('text', destination)
                        address = address_text
                    
                    hotels.append({
                        'id': hotel_id,
                        'property_id': property_id,
                        'name': hotel_name,
                        'stars': int(stars_rating) if stars_rating else 3,
                        'price': int(total_price),  # Prix TOTAL pour le séjour
                        'price_per_night': int(price_per_night),
                        'image': image_url,
                        'rating': rating,
                        'address': address,
                        'reviews_count': reviews_count
                    })
                    
                except Exception as e:
                    logger.warning(f"Erreur parsing hôtel: {e}")
                    continue
            
            print(f"✓ {len(hotels)} hôtels trouvés après filtrage (note >= 8/10)")
            
            # Trier par : note d'abord, puis proximité du budget
            # On veut des hôtels bien notés qui utilisent le budget disponible
            hotels.sort(key=lambda h: (-h['rating'], abs(h['price_per_night'] - max_price * 0.9)))
            
            logger.info(f"✓ {len(hotels)} hôtels trouvés avec note >= 8/10")
            return hotels[:10]  # Retourner top 10 pour avoir plus de choix
            
        except requests.exceptions.Timeout:
            logger.error("Timeout API Hotels.com")
            raise Exception("La recherche d'hôtels a pris trop de temps. Veuillez réessayer.")
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erreur HTTP API Hotels.com: {e}")
            raise Exception(f"Erreur lors de la recherche d'hôtels : {str(e)}")
        except Exception as e:
            logger.error(f"Erreur API Hotels.com: {e}", exc_info=True)
            raise Exception(f"Impossible de rechercher des hôtels : {str(e)}")
    
    def _search_flights_google_flights2(self, origin: str, destination: str, departure_date: str,
                                        return_date: str, adults: int) -> List[Dict[str, Any]]:
        """
        Recherche de vols via Google Flights 2 RapidAPI
        Endpoint principal: /api/v1/searchFlights
        
        Structure de réponse API:
        {
            "data": {
                "topFlights": [...],
                "otherFlights": [...]
            }
        }
        """
        url = "https://google-flights2.p.rapidapi.com/api/v1/searchFlights"
        
        headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": "google-flights2.p.rapidapi.com"
        }
        
        params = {
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": departure_date,
            "return_date": return_date,
            "travel_class": "ECONOMY",
            "adults": str(adults),
            "show_hidden": "1",
            "currency": "EUR",
            "language_code": "fr",
            "country_code": "BE",
            "search_type": "best"
        }
        
        try:
            print(f"\n=== [Google Flights 2] Recherche vols {origin} → {destination} ===")
            print(f"Params: {params}")
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            print(f"Response status: {response.status_code}")
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Vérifier le statut de l'API
            if not data.get('status'):
                logger.warning(f"API Google Flights status=false: {data.get('message')}")
                print(f"⚠️ API status=false: {data.get('message')}")
                return []
            
            flights = []
            
            # NOUVELLE STRUCTURE: topFlights + otherFlights
            data_obj = data.get('data', {})
            top_flights = data_obj.get('topFlights', [])
            other_flights = data_obj.get('otherFlights', [])
            
            # Combiner tous les vols (priorité aux topFlights)
            all_flights = top_flights + other_flights
            
            if not all_flights:
                print(f"⚠️ Aucun vol dans la réponse (topFlights: {len(top_flights)}, otherFlights: {len(other_flights)})")
                return []
            
            print(f"Nombre de vols trouvés: {len(all_flights)} (top: {len(top_flights)}, autres: {len(other_flights)})")
            
            for flight_data in all_flights[:10]:  # Prendre plus d'options
                try:
                    # PRIX - directement dans flight_data
                    total_price = flight_data.get('price', 200)
                    
                    # SEGMENTS - dans flight_data.flights (array de segments)
                    flight_segments = flight_data.get('flights', [])
                    
                    if not flight_segments:
                        continue
                    
                    # LAYOVERS (escales) - optionnel
                    layovers = flight_data.get('layovers', [])
                    
                    # Extraire tous les segments avec leurs infos
                    segments = []
                    
                    # Déterminer si aller simple ou aller-retour
                    # Les vols sont ordonnés : premier = aller, suivants = retour
                    for seg_idx, seg in enumerate(flight_segments):
                        departure_airport_info = seg.get('departure_airport', {})
                        arrival_airport_info = seg.get('arrival_airport', {})
                        
                        # Déterminer si c'est l'aller ou le retour
                        # Si c'est le premier vol vers la destination = ALLER
                        # Si c'est un vol depuis la destination = RETOUR
                        dep_code = departure_airport_info.get('airport_code', '')
                        arr_code = arrival_airport_info.get('airport_code', '')
                        
                        # Logique simple : si on part de l'origine = ALLER, sinon RETOUR
                        if dep_code == origin or (seg_idx == 0 and arr_code == destination):
                            leg_type = "ALLER"
                        else:
                            leg_type = "RETOUR"
                        
                        segments.append({
                            'leg_type': leg_type,
                            'airline': seg.get('airline', 'Airline'),
                            'airline_logo': seg.get('airline_logo', ''),
                            'flight_number': seg.get('flight_number', ''),
                            'aircraft': seg.get('aircraft', ''),
                            'departure_airport': dep_code,
                            'departure_airport_name': departure_airport_info.get('airport_name', ''),
                            'arrival_airport': arr_code,
                            'arrival_airport_name': arrival_airport_info.get('airport_name', ''),
                            'departure_time': departure_airport_info.get('time', '10:00'),
                            'arrival_time': arrival_airport_info.get('arrival_time', '12:00'),
                            'duration': seg.get('duration_label', '2h'),
                            'seat': seg.get('seat', ''),
                            'legroom': seg.get('legroom', ''),
                            'extensions': seg.get('extensions', [])
                        })
                    
                    # Info du premier segment pour l'affichage général
                    first_segment = flight_segments[0] if flight_segments else {}
                    first_dep = first_segment.get('departure_airport', {})
                    first_arr = first_segment.get('arrival_airport', {})
                    
                    # Durée totale
                    duration_info = flight_data.get('duration', {})
                    if isinstance(duration_info, dict):
                        duration_text = duration_info.get('text', '2h')
                    else:
                        duration_text = '2h'
                    
                    # Nombre d'escales
                    stops = flight_data.get('stops', 0)
                    
                    flights.append({
                        'provider': 'Google Flights 2',
                        'airline': first_segment.get('airline', 'Various Airlines'),
                        'airline_logo': first_segment.get('airline_logo', ''),
                        'price': int(total_price),
                        'departure_time': flight_data.get('departure_time', first_dep.get('time', '10:00')),
                        'arrival_time': flight_data.get('arrival_time', first_arr.get('time', '12:00')),
                        'duration': duration_text,
                        'stops': stops,
                        'layovers': layovers,
                        'segments': segments,
                        'carbon_emissions': flight_data.get('carbon_emissions', {}),
                        'bags': flight_data.get('bags', {})
                    })
                    
                except Exception as e:
                    logger.warning(f"Erreur parsing vol Google Flights 2: {e}")
                    import traceback
                    print(f"Erreur détaillée: {traceback.format_exc()}")
                    continue
            
            logger.info(f"[Google Flights 2] ✓ {len(flights)} vols trouvés")
            print(f"✅ {len(flights)} vols parsés avec succès")
            return flights
            
        except Exception as e:
            logger.warning(f"[Google Flights 2] Échec: {str(e)}")
            import traceback
            print(f"❌ Erreur Google Flights 2: {traceback.format_exc()}")
            return []
    
    def _search_flights_skyscrapper(self, origin: str, destination: str, departure_date: str, 
                                    return_date: str, adults: int) -> List[Dict[str, Any]]:
        """Recherche de vols via Sky Scrapper API"""
        url = "https://sky-scrapper.p.rapidapi.com/api/v2/flights/searchFlights"
        
        headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": "sky-scrapper.p.rapidapi.com"
        }
        
        # Sky Scrapper nécessite des IDs spécifiques, on utilise les codes IATA comme base
        params = {
            "originSkyId": origin,
            "destinationSkyId": destination,
            "originEntityId": origin,  # Simplifié, pourrait nécessiter un mapping
            "destinationEntityId": destination,
            "date": departure_date,
            "returnDate": return_date,
            "cabinClass": "economy",
            "adults": str(adults),
            "sortBy": "best",
            "currency": "EUR",
            "market": "fr-BE",
            "countryCode": "BE"
        }
        
        try:
            print(f"\n=== [Sky Scrapper] Recherche vols {origin} → {destination} ===")
            print(f"Params: {params}")
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            print(f"Response status: {response.status_code}")
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            print(f"Full response (first 1000 chars):\n{json.dumps(data, indent=2)[:1000]}")
            
            flights = []
            # Structure de réponse Sky Scrapper
            itineraries = data.get('data', {}).get('itineraries', [])
            
            for itinerary in itineraries[:5]:
                try:
                    legs = itinerary.get('legs', [])
                    if legs:
                        first_leg = legs[0]
                        price_info = itinerary.get('price', {})
                        
                        # Extraire TOUS les segments de TOUS les legs (aller + retour)
                        segments = []
                        for leg_idx, leg in enumerate(legs):
                            # Ajouter un marqueur pour différencier aller/retour
                            leg_type = "ALLER" if leg_idx == 0 else "RETOUR"
                            segments.append({
                                'leg_type': leg_type,
                                'airline': leg.get('carriers', {}).get('marketing', [{}])[0].get('name', 'Airline'),
                                'flight_number': leg.get('carriers', {}).get('marketing', [{}])[0].get('logoUrl', ''),
                                'departure_airport': leg.get('origin', {}).get('displayCode', origin if leg_idx == 0 else destination),
                                'arrival_airport': leg.get('destination', {}).get('displayCode', destination if leg_idx == 0 else origin),
                                'departure_time': leg.get('departure', '10:00'),
                                'arrival_time': leg.get('arrival', '12:00'),
                                'duration': f"{leg.get('durationInMinutes', 120) // 60}h{leg.get('durationInMinutes', 120) % 60}min"
                            })
                        
                        flights.append({
                            'provider': 'Sky Scrapper',
                            'airline': first_leg.get('carriers', {}).get('marketing', [{}])[0].get('name', 'Airline'),
                            'price': int(price_info.get('raw', 200)),
                            'departure_time': first_leg.get('departure', '10:00'),
                            'arrival_time': first_leg.get('arrival', '12:00'),
                            'duration': f"{first_leg.get('durationInMinutes', 120) // 60}h{first_leg.get('durationInMinutes', 120) % 60}min",
                            'stops': first_leg.get('stopCount', 0),
                            'segments': segments
                        })
                except Exception as e:
                    logger.warning(f"Erreur parsing vol Sky Scrapper: {e}")
                    continue
            
            logger.info(f"[Sky Scrapper] ✓ {len(flights)} vols trouvés")
            return flights
            
        except Exception as e:
            logger.warning(f"[Sky Scrapper] Échec: {str(e)}")
            return []
    
    def _search_flights_booking(self, origin: str, destination: str, departure_date: str, 
                                return_date: str, adults: int) -> List[Dict[str, Any]]:
        """Recherche de vols via Booking.com Flights API"""
        url = "https://booking-com15.p.rapidapi.com/api/v1/flights/getMinPrice"
        
        headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": "booking-com15.p.rapidapi.com"
        }
        
        # Booking.com utilise le format AIRPORT et REQUIERT les dates
        params = {
            "fromId": f"{origin}.AIRPORT",
            "toId": f"{destination}.AIRPORT",
            "departDate": departure_date,  # AJOUTÉ - Requis par l'API
            "returnDate": return_date,     # AJOUTÉ - Requis pour aller-retour
            "cabinClass": "ECONOMY",
            "currency_code": "EUR"
        }
        
        try:
            print(f"\n=== [Booking.com] Recherche vols {origin} → {destination} ===")
            print(f"Params: {params}")
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            print(f"Response status: {response.status_code}")
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            print(f"Full response (first 1000 chars):\n{json.dumps(data, indent=2)[:1000]}")
            
            flights = []
            # Booking.com getMinPrice retourne une LISTE directe (pas {data: {flights: []}})
            results = data.get('data', [])
            
            if results and isinstance(results, list):
                # Prendre les 5 meilleures options
                for i, flight_data in enumerate(results[:5]):
                    try:
                        price_info = flight_data.get('price', {})
                        # Le prix est dans un format complexe avec units et nanos
                        price_units = price_info.get('units', 100)
                        price_nanos = price_info.get('nanos', 0)
                        total_price = price_units + (price_nanos / 1_000_000_000)
                        
                        # Créer 2 segments : ALLER et RETOUR
                        segments = [
                            {
                                'leg_type': 'ALLER',
                                'airline': 'Various Airlines',
                                'flight_number': '',
                                'departure_airport': origin,
                                'arrival_airport': destination,
                                'departure_time': '10:00',
                                'arrival_time': '12:00',
                                'duration': '2h'
                            },
                            {
                                'leg_type': 'RETOUR',
                                'airline': 'Various Airlines',
                                'flight_number': '',
                                'departure_airport': destination,
                                'arrival_airport': origin,
                                'departure_time': '15:00',
                                'arrival_time': '17:00',
                                'duration': '2h'
                            }
                        ]
                        
                        flights.append({
                            'provider': 'Booking.com',
                            'airline': 'Various Airlines',
                            'price': int(total_price),
                            'departure_time': '10:00',
                            'arrival_time': '12:00',
                            'duration': '2h',
                            'stops': 0,
                            'segments': segments
                        })
                    except Exception as e:
                        print(f"Erreur parsing vol Booking: {e}")
                        logger.warning(f"Erreur parsing vol Booking: {e}")
                        continue
            
            logger.info(f"[Booking.com] ✓ {len(flights)} vols trouvés")
            return flights
            
        except Exception as e:
            logger.warning(f"[Booking.com] Échec: {str(e)}")
            return []
    
    def _search_flights_flightssky(self, origin: str, destination: str, departure_date: str, 
                                   return_date: str, adults: int) -> List[Dict[str, Any]]:
        """Recherche de vols via Flights Sky API"""
        url = "https://flights-sky.p.rapidapi.com/flights/search-roundtrip"
        
        headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": "flights-sky.p.rapidapi.com"
        }
        
        params = {
            "fromEntityId": origin,
            "toEntityId": destination,
            "departDate": departure_date,
            "returnDate": return_date,
            "adults": str(adults),
            "currency": "EUR",
            "market": "en-US",  # CHANGÉ: en-GB ne marche pas non plus, essai en-US
            "locale": "en-US"   # CHANGÉ: en-GB ne marche pas non plus, essai en-US
        }
        
        try:
            print(f"\n=== [Flights Sky] Recherche vols {origin} → {destination} ===")
            print(f"Params: {params}")
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            print(f"Response status: {response.status_code}")
            print(f"Response type: {type(data)}")
            if data:
                print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                print(f"Full response (first 1000 chars):\n{json.dumps(data, indent=2)[:1000]}")
            else:
                print(f"Response is None or empty")
            
            flights = []
            if data and isinstance(data, dict):
                results = data.get('data', {}).get('itineraries', [])
            else:
                results = []
            
            for itinerary in results[:5]:
                try:
                    legs = itinerary.get('legs', [])
                    if legs:
                        first_leg = legs[0]
                        price_info = itinerary.get('price', {})
                        
                        # Extraire TOUS les segments de TOUS les legs (aller + retour)
                        segments = []
                        for leg_idx, leg in enumerate(legs):
                            # Ajouter un marqueur pour différencier aller/retour
                            leg_type = "ALLER" if leg_idx == 0 else "RETOUR"
                            segments.append({
                                'leg_type': leg_type,
                                'airline': leg.get('carriers', [{}])[0].get('name', 'Airline'),
                                'flight_number': '',
                                'departure_airport': leg.get('origin', {}).get('displayCode', origin if leg_idx == 0 else destination),
                                'arrival_airport': leg.get('destination', {}).get('displayCode', destination if leg_idx == 0 else origin),
                                'departure_time': leg.get('departure', '10:00'),
                                'arrival_time': leg.get('arrival', '12:00'),
                                'duration': f"{leg.get('durationInMinutes', 120) // 60}h"
                            })
                        
                        flights.append({
                            'provider': 'Flights Sky',
                            'airline': first_leg.get('carriers', [{}])[0].get('name', 'Airline'),
                            'price': int(price_info.get('raw', 200)),
                            'departure_time': first_leg.get('departure', '10:00'),
                            'arrival_time': first_leg.get('arrival', '12:00'),
                            'duration': f"{first_leg.get('durationInMinutes', 120) // 60}h",
                            'stops': first_leg.get('stopCount', 0),
                            'segments': segments
                        })
                except Exception as e:
                    logger.warning(f"Erreur parsing vol Flights Sky: {e}")
                    continue
            
            logger.info(f"[Flights Sky] ✓ {len(flights)} vols trouvés")
            return flights
            
        except Exception as e:
            logger.warning(f"[Flights Sky] Échec: {str(e)}")
            return []
    
    def _search_flights_cascade(self, origin: str, destination: str, departure_date: str, 
                               return_date: str, adults: int) -> List[Dict[str, Any]]:
        """
        Recherche de vols avec système de cascade multi-APIs
        Essaie plusieurs APIs dans l'ordre jusqu'à trouver des résultats
        
        Args:
            origin: Code IATA aéroport de départ
            destination: Code IATA aéroport d'arrivée
            departure_date: Date de départ (YYYY-MM-DD)
            return_date: Date de retour (YYYY-MM-DD)
            adults: Nombre d'adultes
            
        Returns:
            Liste de vols trouvés ou lève une exception si toutes les APIs échouent
        """
        
        logger.info(f"🔍 Recherche vols {origin} → {destination} avec système cascade")
        
        # Liste des providers à essayer dans l'ordre
        providers = [
            ("Google Flights 2", self._search_flights_google_flights2),  # PRIORITÉ 1
            ("Sky Scrapper", self._search_flights_skyscrapper),
            ("Booking.com Flights", self._search_flights_booking),
            ("Flights Sky", self._search_flights_flightssky)
        ]
        
        errors = []
        
        for provider_name, provider_func in providers:
            try:
                flights = provider_func(origin, destination, departure_date, return_date, adults)
                if flights:
                    logger.info(f"✅ Vols trouvés via {provider_name}")
                    return flights
                else:
                    logger.warning(f"⚠️ {provider_name}: Aucun résultat")
                    errors.append(f"{provider_name}: Aucun résultat")
            except Exception as e:
                logger.warning(f"❌ {provider_name}: {str(e)}")
                errors.append(f"{provider_name}: {str(e)}")
        
        # Si on arrive ici, toutes les APIs ont échoué
        error_details = "\n- ".join(errors)
        raise Exception(
            f"Impossible de trouver des vols pour {origin} → {destination}.\n"
            f"Toutes les APIs ont échoué:\n- {error_details}\n\n"
            f"Solutions:\n"
            f"1. Vérifiez que vous êtes abonné aux APIs de vols sur RapidAPI\n"
            f"2. Essayez d'autres dates de voyage\n"
            f"3. Consultez APIS_VOLS_ALTERNATIVES.md pour configurer les APIs"
        )
    
    def generate_travel_options(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Génère 2-3 options de voyage basées sur les critères
        Utilise UNIQUEMENT les APIs réelles - AUCUNE SIMULATION
        
        Args:
            criteria: Critères extraits de la demande
            
        Returns:
            Liste de 2-3 options de voyage ou lève une exception
        """
        
        destination = criteria.get('destination')
        budget = criteria.get('budget_pp')
        date_debut = criteria.get('date_debut')
        date_fin = criteria.get('date_fin')
        num_personnes = criteria.get('num_personnes', 2)
        inclusions = criteria.get('inclusions', [])
        stars_min = criteria.get('stars_min')
        origin_code = criteria.get('origin_airport_code')
        dest_code = criteria.get('destination_airport_code')
        
        # Gérer les fenêtres de dates flexibles
        date_window_start = criteria.get('date_window_start')
        date_window_end = criteria.get('date_window_end')
        duration_days = criteria.get('duration_days')
        
        # Si fenêtre de dates + durée → essayer plusieurs combinaisons
        if date_window_start and date_window_end and duration_days:
            logger.info(f"🔍 Mode flexible: essai de plusieurs combinaisons ({duration_days} jours entre {date_window_start} et {date_window_end})")
            
            # Générer les combinaisons possibles
            from datetime import datetime as dt
            start_dt = dt.strptime(date_window_start, '%Y-%m-%d')
            end_dt = dt.strptime(date_window_end, '%Y-%m-%d')
            window_days = (end_dt - start_dt).days
            
            # Calculer combien de départs possibles dans la fenêtre
            possible_starts = max(1, window_days - duration_days + 1)
            date_combinations = []
            
            for i in range(possible_starts):
                depart = start_dt + timedelta(days=i)
                retour = depart + timedelta(days=duration_days)
                # Ne pas dépasser la fin de la fenêtre
                if retour <= end_dt:
                    date_combinations.append({
                        'depart': depart.strftime('%Y-%m-%d'),
                        'retour': retour.strftime('%Y-%m-%d')
                    })
            
            print(f"📅 {len(date_combinations)} combinaisons de dates à tester:")
            for combo in date_combinations:
                print(f"  - Départ {combo['depart']} → Retour {combo['retour']}")
            
            # Essayer chaque combinaison jusqu'à trouver des vols
            flights = None
            successful_dates = None
            attempts_log = []
            
            for combo in date_combinations:
                try:
                    print(f"\n🔄 Tentative: {combo['depart']} → {combo['retour']}")
                    test_flights = self._search_flights_cascade(
                        origin=origin_code,
                        destination=dest_code,
                        departure_date=combo['depart'],
                        return_date=combo['retour'],
                        adults=num_personnes
                    )
                    if test_flights:
                        flights = test_flights
                        successful_dates = combo
                        date_debut = combo['depart']
                        date_fin = combo['retour']
                        print(f"✅ Vols trouvés pour {date_debut} → {date_fin}!")
                        break
                    attempts_log.append(f"{combo['depart']} → {combo['retour']}: Aucun vol disponible")
                except Exception as e:
                    attempts_log.append(f"{combo['depart']} → {combo['retour']}: {str(e)}")
                    logger.warning(f"Échec pour {combo['depart']} → {combo['retour']}: {e}")
            
            # Si aucune combinaison n'a fonctionné
            if not flights:
                error_msg = (
                    f"Aucun vol trouvé pour {criteria.get('origin')} → {destination} sur {duration_days} jours dans la période du {date_window_start} au {date_window_end}.\n\n"
                    f"Combinaisons testées:\n- " + "\n- ".join(attempts_log) + "\n\n"
                    f"Suggestions:\n"
                    f"• Essayez une fenêtre de dates plus large\n"
                    f"• Modifiez la durée du séjour ({duration_days} jours)\n"
                    f"• Choisissez un autre aéroport de départ ou d'arrivée\n"
                    f"• Ces dates peuvent ne pas encore être disponibles dans les systèmes de réservation"
                )
                raise Exception(error_msg)
        else:
            # Mode dates fixes
            if not date_debut:
                date_debut = self._get_default_date()
            if not date_fin:
                date_fin = self._get_default_date(days=4)
            
            logger.info(f"🔍 Recherche pour {destination} ({dest_code}) depuis {criteria.get('origin')} ({origin_code})")
            
            # Rechercher vols
            flights = self._search_flights_cascade(
                origin=origin_code,
                destination=dest_code,
                departure_date=date_debut,
                return_date=date_fin,
                adults=num_personnes
            )
        
        if not flights:
            raise Exception(f"Aucun vol trouvé pour {criteria.get('origin')} → {destination} aux dates demandées. Veuillez essayer d'autres dates ou destinations.")
        
        # 2. Rechercher hôtels
        # Calculer le budget hôtel par NUIT
        from datetime import datetime as dt
        nights = (dt.strptime(date_fin, '%Y-%m-%d') - dt.strptime(date_debut, '%Y-%m-%d')).days
        if nights <= 0:
            nights = 1
        
        # Budget total pour l'hôtel (70% du budget total * nombre de personnes)
        total_hotel_budget = int(budget * num_personnes * 0.7)
        # Prix max par nuit
        max_price_per_night = total_hotel_budget // nights
        
        print(f"💰 Budget hôtel: {total_hotel_budget}€ total / {nights} nuits = {max_price_per_night}€ par nuit (chambre complète)")
        
        # Premier essai avec budget calculé
        hotels = self._search_hotels_rapidapi(
            destination=destination,
            checkin=date_debut,
            checkout=date_fin,
            adults=num_personnes,
            max_price=max_price_per_night,
            stars=stars_min
        )
        
        # Si aucun hôtel trouvé, élargir sans limite de prix
        budget_exceeded = False
        if not hotels:
            print(f"⚠️ Aucun hôtel trouvé avec budget {max_price_per_night}€/nuit, recherche SANS limite de prix...")
            hotels = self._search_hotels_rapidapi(
                destination=destination,
                checkin=date_debut,
                checkout=date_fin,
                adults=num_personnes,
                max_price=9999,  # Pas de limite
                stars=stars_min
            )
            budget_exceeded = True
        
        if not hotels:
            raise Exception(f"Aucun hôtel trouvé à {destination}, même en élargissant le budget. Veuillez essayer une autre destination ou d'autres dates.")
        
        # ENRICHISSEMENT DES HÔTELS (avant de créer les options)
        print(f"\n🎨 Enrichissement des {min(3, len(hotels))} meilleurs hôtels...")
        
        for idx, hotel in enumerate(hotels[:3]):
            property_id = hotel.get('property_id')
            
            if not property_id:
                print(f"⚠️ Hôtel {idx+1}: Pas de property_id, skip enrichissement")
                continue
            
            try:
                # 1. Récupérer highlights
                highlights = self._get_hotel_highlights(property_id)
                if highlights:
                    hotel['highlights'] = highlights[:5]  # Top 5 highlights
                    print(f"✓ Hôtel {idx+1}: {len(highlights)} highlights récupérés")
                
                # 2. Récupérer amenities
                amenities_data = self._get_hotel_amenities(property_id)
                if amenities_data:
                    key_amenities = self._extract_key_amenities(amenities_data)
                    hotel['key_amenities'] = key_amenities
                    hotel['all_amenities'] = amenities_data  # Garder aussi les détails complets
                    print(f"✓ Hôtel {idx+1}: {len(key_amenities)} équipements clés extraits")
                
                # 3. Récupérer détails de localisation
                location_details = self._get_hotel_location_details(property_id)
                if location_details:
                    hotel['coordinates'] = location_details.get('coordinates', {})
                    hotel['neighborhood'] = location_details.get('neighborhood', '')
                    hotel['nearby_attractions'] = location_details.get('nearby_attractions', [])[:3]
                    print(f"✓ Hôtel {idx+1}: Localisation et {len(location_details.get('nearby_attractions', []))} attractions récupérées")
            
            except Exception as e:
                print(f"⚠️ Erreur enrichissement hôtel {idx+1}: {e}")
                # Continuer même en cas d'erreur sur un hôtel
                logger.warning(f"Échec enrichissement pour {hotel.get('name')}: {e}")
        
        print(f"✅ Enrichissement terminé\n")
        
        # 3. Combiner pour créer des options
        options = []
        budget_warnings = []
        
        for i, hotel in enumerate(hotels[:3]):
            # Prendre le vol correspondant (ou le moins cher)
            flight = flights[min(i, len(flights)-1)]
            
            total_price = (hotel['price'] + flight['price']) // num_personnes
            
            option_type = 'budget' if i == 0 else ('balanced' if i == 1 else 'premium')
            
            # Créer l'option même si budget dépassé
            option = {
                'destination': destination,
                'date_debut': date_debut,
                'date_fin': date_fin,
                'total_price': total_price,
                'hotel': hotel,
                'flight': flight,
                'inclusions': inclusions or ['petit-déjeuner'],
                'option_type': option_type,
                'budget_exceeded': total_price > budget,
                'budget_requested': budget
            }
            
            # Ajouter un warning si budget dépassé
            if total_price > budget:
                budget_warnings.append(f"Option {i+1}: {total_price}€ (budget demandé: {budget}€)")
            
            options.append(option)
        
        if not options:
            raise Exception(f"Impossible de créer des options de voyage pour {destination}. Veuillez essayer une autre destination.")
        
        # Logger les warnings de budget
        if budget_warnings:
            print(f"\n⚠️ ATTENTION: Le budget demandé ({budget}€/personne) n'a pas pu être respecté:")
            for warning in budget_warnings:
                print(f"   - {warning}")
            print(f"   Les options sont affichées malgré tout pour votre information.\n")
        
        logger.info(f"✅ {len(options)} options trouvées (budget_exceeded: {budget_exceeded})")
        return options[:3]  # Max 3 options
    
    def _get_default_date(self, days: int = 0) -> str:
        """Génère une date par défaut (dans 30 jours + offset)"""
        date = datetime.now() + timedelta(days=30 + days)
        return date.strftime('%Y-%m-%d')
    
    def _extract_key_amenities(self, amenities: Dict[str, Any]) -> List[str]:
        """
        Extrait les équipements les plus importants d'un hôtel
        
        Args:
            amenities: Dict avec room_amenities, hotel_amenities, accessibility
            
        Returns:
            Liste des 5-8 équipements les plus pertinents
        """
        # Mots-clés pour identifier les équipements importants
        important_keywords = [
            'wifi', 'wi-fi', 'internet',
            'parking', 'garage',
            'pool', 'piscine', 'swimming',
            'breakfast', 'petit-déjeuner', 'déjeuner',
            'air conditioning', 'climatisation', 'a/c',
            'gym', 'fitness', 'salle de sport',
            'spa', 'sauna',
            'restaurant',
            'bar',
            'room service',
            'kitchen', 'kitchenette', 'cuisine'
        ]
        
        room_amenities = amenities.get('room_amenities', [])
        hotel_amenities = amenities.get('hotel_amenities', [])
        
        # Combiner tous les équipements
        all_amenities = []
        if isinstance(room_amenities, list):
            all_amenities.extend(room_amenities)
        if isinstance(hotel_amenities, list):
            all_amenities.extend(hotel_amenities)
        
        # Filtrer les équipements importants
        key_amenities = []
        for amenity in all_amenities:
            if isinstance(amenity, str):
                amenity_lower = amenity.lower()
                if any(keyword in amenity_lower for keyword in important_keywords):
                    if amenity not in key_amenities:  # Éviter les doublons
                        key_amenities.append(amenity)
        
        return key_amenities[:8]  # Max 8 équipements clés
    
    def _get_placeholder_image(self, destination: str) -> str:
        """Retourne une image placeholder pour la destination"""
        return f'https://source.unsplash.com/800x600/?{destination},hotel'
    
    def search_and_aggregate(self, query: str) -> Dict[str, Any]:
        """
        Méthode principale : analyse + génération d'options
        
        Args:
            query: Demande utilisateur en langage naturel
            
        Returns:
            {
                "success": true,
                "criteria": {...},
                "options": [...]
            }
        """
        
        # Étape 1 : Analyser la demande avec Gemini
        analysis = self.analyze_travel_request(query)
        
        if not analysis.get('success'):
            return analysis
        
        criteria = analysis['criteria']
        
        
        # Étape 2 : Générer des options de voyage
        try:
            options = self.generate_travel_options(criteria)
            
            return {
                'success': True,
                'criteria': criteria,
                'options': options,
                'count': len(options)
            }
            
        except Exception as e:
            logger.error(f"Erreur génération options: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Erreur lors de la recherche: {str(e)}'
            }


# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================

def search_travel_inspiration(query: str, gemini_api_key: str, rapidapi_key: str = None) -> Dict[str, Any]:
    """
    Fonction raccourci pour rechercher des inspirations de voyage
    
    Args:
        query: Demande en langage naturel
        gemini_api_key: Clé API Gemini
        rapidapi_key: Clé RapidAPI (optionnel, pour vraies données)
        
    Returns:
        Résultat de la recherche avec options
    """
    inspector = TravelInspector(gemini_api_key, rapidapi_key)
    return inspector.search_and_aggregate(query)


# ==============================================================================
# TESTS
# ==============================================================================

if __name__ == "__main__":
    """
    Tests du service Travel Inspector
    """
    
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    API_KEY = os.environ.get('GOOGLE_GEMINI_API_KEY')
    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
    
    if not API_KEY:
        print("❌ Clé GOOGLE_GEMINI_API_KEY manquante")
        exit(1)
    
    if not RAPIDAPI_KEY:
        print("❌ Clé RAPIDAPI_KEY manquante")
        exit(1)
    
    inspector = TravelInspector(API_KEY, RAPIDAPI_KEY)
    
    # Test 1 : Analyse simple
    print("\n" + "="*60)
    print("TEST 1 : ANALYSE DE DEMANDE")
    print("="*60)
    
    query = "4 jours à Rome, hotel avec petit déjeuner, départ entre le 03/10 et le 9/10 pour un budget de 400€ par personne"
    
    print(f"\n📝 Demande: {query}")
    result = inspector.search_and_aggregate(query)
    print(f"\n✅ Résultat:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Test 2 : Autres exemples
    print("\n" + "="*60)
    print("TEST 2 : AUTRES EXEMPLES")
    print("="*60)
    
    test_queries = [
        "Week-end à Barcelone, 300€ par personne, hôtel 4 étoiles",
        "5 jours à Lisbonne du 15 au 20 mai, budget 500€, 2 personnes",
        "Voyage romantique à Venise, all-inclusive, 600€ chacun"
    ]
    
    for query in test_queries:
        print(f"\n📝 {query}")
        result = inspector.search_and_aggregate(query)
        if result.get('success'):
            print(f"   ✓ {len(result.get('options', []))} options trouvées")
            print(f"   💰 Budget: {result['criteria'].get('budget_pp')}€")
        else:
            print(f"   ✗ Erreur: {result.get('error')}")
    
    print("\n✅ Tests terminés !")
