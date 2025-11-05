# services/api_gatherer.py
"""
Rassemble les données depuis les APIs externes (Google Places, YouTube, Gemini)
pour enrichir les fiches de voyage avec des données réelles.
Version complète adaptée d'odyssee-app pour odyssee-saas.
"""

import requests
import json
from typing import Dict, Any, List
import google.generativeai as genai


class TripDataGatherer:
    """Collecte toutes les données nécessaires pour générer une fiche de voyage complète"""
    
    def __init__(self, google_api_key: str):
        """
        Initialise le gatherer avec la clé API Google
        
        Args:
            google_api_key: Clé API Google (utilisée pour Places, YouTube et Gemini)
        """
        self.google_api_key = google_api_key
        
        if google_api_key:
            genai.configure(api_key=google_api_key)
            print("✅ API Google configurée")
        else:
            print("⚠️ Aucune clé API Google fournie")
    
    def get_hotel_photos(self, hotel_name: str, destination: str) -> List[str]:
        """
        Récupère les photos réelles d'un hôtel via Google Places
        
        Args:
            hotel_name: Nom de l'hôtel
            destination: Destination (ville/pays)
            
        Returns:
            Liste d'URLs de photos
        """
        if not self.google_api_key:
            return []
        
        try:
            # 1. Recherche de l'hôtel
            search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            search_params = {
                'query': f'"{hotel_name}" "{destination}" hotel',
                'key': self.google_api_key,
                'fields': 'photos,place_id'
            }
            
            search_response = requests.get(search_url, params=search_params, timeout=15)
            
            if search_response.status_code != 200:
                print(f"❌ Erreur recherche hôtel: HTTP {search_response.status_code}")
                return []
            
            search_data = search_response.json()
            
            if not search_data.get('results'):
                print(f"⚠️ Aucun résultat pour {hotel_name}")
                return []
            
            # 2. Récupérer les détails avec les photos
            place_id = search_data['results'][0].get('place_id')
            
            details_url = "https://maps.googleapis.com/maps/api/place/details/json"
            details_params = {
                'place_id': place_id,
                'fields': 'photos',
                'key': self.google_api_key
            }
            
            details_response = requests.get(details_url, params=details_params, timeout=15)
            
            if details_response.status_code == 200:
                photos = details_response.json().get('result', {}).get('photos', [])
                
                # Générer les URLs des photos
                photo_urls = []
                for photo in photos:
                    photo_ref = photo.get('photo_reference')
                    if photo_ref:
                        url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={self.google_api_key}"
                        photo_urls.append(url)
                
                return photo_urls
            
            return []
            
        except Exception as e:
            print(f"❌ Erreur récupération photos: {e}")
            return []
    
    def get_hotel_reviews(self, hotel_name: str, destination: str) -> Dict[str, Any]:
        """
        Récupère les avis Google d'un hôtel
        
        Args:
            hotel_name: Nom de l'hôtel
            destination: Destination
            
        Returns:
            Dictionnaire avec reviews, rating et total_reviews
        """
        if not self.google_api_key:
            return {'reviews': [], 'rating': 0, 'total_reviews': 0}
        
        try:
            # 1. Recherche de l'hôtel
            search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            search_params = {
                'query': f'"{hotel_name}" "{destination}" hotel',
                'key': self.google_api_key
            }
            
            search_response = requests.get(search_url, params=search_params, timeout=15)
            
            if search_response.status_code != 200:
                return {'reviews': [], 'rating': 0, 'total_reviews': 0}
            
            search_data = search_response.json()
            
            if not search_data.get('results'):
                return {'reviews': [], 'rating': 0, 'total_reviews': 0}
            
            place_id = search_data['results'][0].get('place_id')
            
            # 2. Récupérer les avis
            details_url = "https://maps.googleapis.com/maps/api/place/details/json"
            details_params = {
                'place_id': place_id,
                'fields': 'reviews,rating,user_ratings_total',
                'key': self.google_api_key,
                'language': 'fr'
            }
            
            details_response = requests.get(details_url, params=details_params, timeout=15)
            
            if details_response.status_code == 200:
                result = details_response.json().get('result', {})
                all_reviews = result.get('reviews', [])
                
                # Trier par note (meilleurs avis en premier)
                sorted_reviews = sorted(
                    all_reviews,
                    key=lambda r: (r.get('rating', 0), r.get('time', 0)),
                    reverse=True
                )
                
                # Formater les avis (seulement 4⭐ et plus)
                formatted_reviews = []
                for review in sorted_reviews:
                    if review.get('rating', 0) >= 4:
                        formatted_reviews.append({
                            'rating': '⭐' * review.get('rating', 0),
                            'author': review.get('author_name', 'Anonyme'),
                            'text': review.get('text', '')[:400] + '...',
                            'date': review.get('relative_time_description', '')
                        })
                
                return {
                    'reviews': formatted_reviews,
                    'rating': result.get('rating', 0),
                    'total_reviews': result.get('user_ratings_total', 0)
                }
            
            return {'reviews': [], 'rating': 0, 'total_reviews': 0}
            
        except Exception as e:
            print(f"❌ Erreur récupération avis: {e}")
            return {'reviews': [], 'rating': 0, 'total_reviews': 0}
    
    def get_youtube_videos(self, hotel_name: str, destination: str) -> List[Dict[str, str]]:
        """
        Récupère des vidéos YouTube sur l'hôtel/destination
        
        Args:
            hotel_name: Nom de l'hôtel
            destination: Destination
            
        Returns:
            Liste de vidéos avec id et title
        """
        if not self.google_api_key:
            return []
        
        try:
            youtube_url = "https://www.googleapis.com/youtube/v3/search"
            youtube_params = {
                'part': 'snippet',
                'q': f'"{hotel_name}" "{destination}" hotel review tour',
                'type': 'video',
                'maxResults': 4,
                'order': 'relevance',
                'key': self.google_api_key
            }
            
            youtube_response = requests.get(youtube_url, params=youtube_params, timeout=15)
            
            if youtube_response.status_code == 200:
                videos = []
                for item in youtube_response.json().get('items', []):
                    video_id = item.get('id', {}).get('videoId')
                    if video_id:
                        videos.append({
                            'id': video_id,
                            'title': item['snippet']['title']
                        })
                return videos
            
            return []
            
        except Exception as e:
            print(f"❌ Erreur API YouTube: {e}")
            return []
    
    def get_attraction_image(self, attraction_name: str, destination: str) -> str:
        """
        Récupère l'image d'une attraction via Google Places
        
        Args:
            attraction_name: Nom de l'attraction
            destination: Destination
            
        Returns:
            URL de l'image ou None
        """
        if not self.google_api_key:
            return None
        
        print(f"ℹ️ Recherche d'une image réelle pour : {attraction_name} à {destination}")
        
        try:
            search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            search_params = {
                'query': f'"{attraction_name}" "{destination}"',
                'key': self.google_api_key,
                'fields': 'photos'
            }
            
            search_response = requests.get(search_url, params=search_params, timeout=15)
            
            if search_response.status_code == 200:
                search_data = search_response.json()
                
                if search_data.get('results') and search_data['results'][0].get('photos'):
                    photo_reference = search_data['results'][0]['photos'][0].get('photo_reference')
                    
                    if photo_reference:
                        return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_reference}&key={self.google_api_key}"
            
            return None
            
        except Exception as e:
            print(f"❌ Erreur API Image Attraction: {e}")
            return None
    
    def get_attractions_and_restaurants(self, destination: str) -> Dict[str, Any]:
        """
        Génère une liste d'attractions et restaurants via Gemini AI
        
        Args:
            destination: Destination
            
        Returns:
            Dictionnaire avec attractions par catégorie et restaurants
        """
        if not self.google_api_key:
            return {"attractions": [], "restaurants": []}
        
        try:
            # Utiliser Gemini 2.5 Flash (le plus récent et efficace)
            model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
            
            prompt = f'''Donne-moi 8 points d'intérêt pour {destination} et une sélection de 3 des meilleurs restaurants. 
Réponds UNIQUEMENT en JSON valide :
{{
    "attractions": [
        {{"name": "Nom de l'attraction", "type": "plage|culture|gastronomie|activite"}}
    ],
    "restaurants": [
        {{"name": "Nom du restaurant"}}
    ]
}}'''
            
            response = model.generate_content(prompt)
            response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
            
            parsed_data = json.loads(response_text)
            
            return parsed_data
            
        except Exception as e:
            print(f"❌ Erreur API Gemini: {e}")
            return {"attractions": [], "restaurants": []}
    
    def generate_whatsapp_catchphrase(self, trip_details: Dict[str, str]) -> str:
        """
        Génère une phrase marketing accrocheuse pour WhatsApp
        
        Args:
            trip_details: hotel_name et destination
            
        Returns:
            Phrase marketing
        """
        if not self.google_api_key:
            return "Une offre à ne pas manquer !"
        
        try:
            model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
            
            prompt = f"""Crée une très courte phrase marketing (maximum 15 mots) pour une publication WhatsApp concernant un voyage.
Voici les détails : Hôtel '{trip_details['hotel_name']}' à {trip_details['destination']}.
Le but est de donner envie de cliquer sur le lien de l'offre. Sois percutant et inspirant.
Exemples : 'Le paradis vous attend à prix d'ami ! 🌴', 'Évadez-vous sous le soleil de {trip_details['destination']} à un tarif jamais vu !', 
'Saisissez cette chance unique de découvrir {trip_details['hotel_name']} ! ✨'"""
            
            response = model.generate_content(prompt)
            clean_text = response.text.strip().replace('*', '').replace('"', '')
            
            return clean_text
            
        except Exception as e:
            print(f"❌ Erreur API Gemini (catchphrase): {e}")
            return "Découvrez notre offre exclusive pour cette destination de rêve !"
    
    def gather_all_data(self, hotel_name: str, destination: str) -> Dict[str, Any]:
        """
        Point d'entrée principal : collecte TOUTES les données pour la fiche
        
        Args:
            hotel_name: Nom de l'hôtel
            destination: Destination
            
        Returns:
            Dictionnaire complet avec photos, avis, vidéos, attractions, restaurants
        """
        print(f"\n🔍 Collecte des données pour {hotel_name} à {destination}")
        
        # 1. Attractions et restaurants via Gemini
        gemini_data = self.get_attractions_and_restaurants(destination)
        attractions_list = gemini_data.get("attractions", [])
        restaurants_list = gemini_data.get("restaurants", [])
        
        # 2. Organiser les attractions par catégorie
        attractions_by_category = {
            'plages': [],
            'culture': [],
            'gastronomie': [],
            'activites': []
        }
        
        for attr in attractions_list:
            category = attr.get('type', 'activites').replace('activite', 'activites')
            if category in attractions_by_category:
                attractions_by_category[category].append(attr.get('name', ''))
        
        # 3. Image d'une attraction culturelle
        cultural_attraction_image = None
        if attractions_by_category.get('culture'):
            if attractions_by_category['culture']:  # S'assurer que la liste n'est pas vide
                first_cultural_attraction = attractions_by_category['culture'][0]
                cultural_attraction_image = self.get_attraction_image(first_cultural_attraction, destination)
        
        # 4. Avis de l'hôtel
        reviews_data = self.get_hotel_reviews(hotel_name, destination)
        
        # 5. Retourner toutes les données
        return {
            'photos': self.get_hotel_photos(hotel_name, destination),
            'reviews': reviews_data.get('reviews', []),
            'hotel_rating': reviews_data.get('rating', 0),
            'total_reviews': reviews_data.get('total_reviews', 0),
            'videos': self.get_youtube_videos(hotel_name, destination),
            'attractions': attractions_by_category,
            'restaurants': restaurants_list,
            'cultural_attraction_image': cultural_attraction_image
        }


def format_day_trip_program(raw_description: str, gemini_key: str) -> str:
    """
    Reformule la description brute d'une excursion en programme HTML attractif
    
    Args:
        raw_description: Description brute de l'excursion
        gemini_key: Clé API Gemini
        
    Returns:
        HTML formaté avec emojis et structure chronologique
    """
    if not gemini_key or not raw_description:
        return f'<p class="text-gray-700">{raw_description}</p>'
    
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
        
        prompt = f"""Transforme cette description d'excursion en un programme HTML attractif avec emojis.
Crée une liste chronologique claire et engageante.

Description brute :
{raw_description}

Format attendu (exemple) :
<div class="flex items-start mb-3">
    <div class="text-2xl mr-3">🕐</div>
    <div>
        <h5 class="font-semibold">08:00 - Départ</h5>
        <p class="text-sm text-gray-600">Départ en autocar confortable depuis Bruxelles</p>
    </div>
</div>
<div class="flex items-start mb-3">
    <div class="text-2xl mr-3">☕</div>
    <div>
        <h5 class="font-semibold">10:30 - Pause café</h5>
        <p class="text-sm text-gray-600">Pause détente avec boissons chaudes</p>
    </div>
</div>

Réponds UNIQUEMENT avec le HTML, sans markdown ni balises code.
"""
        
        response = model.generate_content(prompt)
        return response.text.strip().replace("```html", "").replace("```", "").strip()
        
    except Exception as e:
        print(f"❌ Erreur formatage programme: {e}")
        return f'<p class="text-gray-700">{raw_description}</p>'


def generate_activity_description(activity_name: str, city: str, gemini_key: str) -> str:
    """
    Génère une description attractive d'une activité avec Gemini
    
    Args:
        activity_name: Nom de l'activité
        city: Ville/destination
        gemini_key: Clé API Gemini
        
    Returns:
        Description attractive
    """
    if not gemini_key:
        return ""
    
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
        
        prompt = f"""Écris un court paragraphe attractif (max 100 mots) sur "{activity_name}" à {city}.
Style marketing enthousiaste avec 1-2 emojis.
Focus sur l'expérience unique et les émotions.

Réponds directement avec le texte, sans titre ni markdown.
"""
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        print(f"❌ Erreur génération description: {e}")
        return ""


def gather_day_trip_data(form_data: Dict[str, Any], agency_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Collecte les données pour une excursion d'un jour
    
    Args:
        form_data: Données du formulaire d'excursion
        agency_config: Configuration de l'agence (clés API)
        
    Returns:
        Dictionnaire avec données enrichies pour l'excursion
    """
    google_api_key = agency_config.get('google_api_key')
    
    if not google_api_key:
        print("⚠️ Aucune clé Google API - génération avec données limitées")
        return {
            'success': False,
            'error': 'Clé Google API manquante',
            'form_data': form_data,
            'api_data': {},
            'margin': 0,
            'savings': 0
        }
    
    destination = form_data.get('destination', '')
    
    result = {
        'success': True,
        'form_data': form_data,
        'api_data': {},
        'margin': 0,
        'savings': 0,
        'comparison_total': 0
    }
    
    try:
        # 1. Rechercher le lieu (ville ou attraction)
        search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        search_params = {
            'query': destination,
            'key': google_api_key
        }
        
        search_response = requests.get(search_url, params=search_params, timeout=15)
        
        if search_response.status_code == 200:
            search_data = search_response.json()
            
            if search_data.get('results'):
                place_id = search_data['results'][0].get('place_id')
                
                # 2. Photos de la destination (max 6)
                details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                details_params = {
                    'place_id': place_id,
                    'fields': 'photos',
                    'key': google_api_key
                }
                
                details_response = requests.get(details_url, params=details_params, timeout=15)
                
                if details_response.status_code == 200:
                    photos = details_response.json().get('result', {}).get('photos', [])
                    photo_urls = []
                    
                    for photo in photos[:6]:
                        photo_ref = photo.get('photo_reference')
                        if photo_ref:
                            url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={google_api_key}"
                            photo_urls.append(url)
                    
                    result['api_data']['photos'] = photo_urls
                
                # 3. Extraire une activité de la description utilisateur avec Gemini
                if form_data.get('day_trip_description'):
                    try:
                        genai.configure(api_key=google_api_key)
                        model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
                        
                        extract_prompt = f"""Analyse cette description d'excursion et extrais UNE activité/attraction principale mentionnée.

Description :
{form_data['day_trip_description']}

Réponds en JSON :
{{
    "activity_name": "Nom de l'activité/attraction"
}}

Si plusieurs activités sont mentionnées, choisis la plus importante. Réponds UNIQUEMENT avec le JSON, sans markdown.
"""
                        
                        extract_response = model.generate_content(extract_prompt)
                        activity_json = extract_response.text.strip().replace("```json", "").replace("```", "").strip()
                        activity_data = json.loads(activity_json)
                        activity_name = activity_data.get('activity_name', '')
                        
                        if activity_name:
                            # Chercher la photo de cette activité
                            activity_search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
                            activity_search_params = {
                                'query': f'{activity_name} {destination}',
                                'key': google_api_key
                            }
                            
                            activity_response = requests.get(activity_search_url, params=activity_search_params, timeout=15)
                            
                            activity_photo = None
                            if activity_response.status_code == 200:
                                activity_results = activity_response.json().get('results', [])
                                if activity_results and activity_results[0].get('photos'):
                                    photo_ref = activity_results[0]['photos'][0].get('photo_reference')
                                    if photo_ref:
                                        activity_photo = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={google_api_key}"
                            
                            # Générer description attractive
                            activity_desc = generate_activity_description(
                                activity_name,
                                destination,
                                google_api_key
                            )
                            
                            result['api_data']['featured_activity'] = {
                                'name': activity_name,
                                'photo': activity_photo,
                                'description': activity_desc
                            }
                    except Exception as e:
                        print(f"❌ Erreur extraction activité: {e}")
        
        # 5. Reformater le programme avec Gemini
        if form_data.get('day_trip_description'):
            program_html = format_day_trip_program(
                form_data['day_trip_description'],
                google_api_key
            )
            result['api_data']['program_formatted'] = program_html
        
        # Valeurs par défaut pour compatibilité
        result['api_data'].setdefault('photos', [])
        result['api_data'].setdefault('videos', [])
        result['api_data'].setdefault('reviews', [])
        result['api_data'].setdefault('attractions', {})
        result['api_data'].setdefault('restaurants', [])
        
    except Exception as e:
        print(f"❌ Erreur enrichissement excursion: {e}")
    
    return result


def gather_trip_data(form_data: Dict[str, Any], agency_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Point d'entrée pour collecter toutes les données nécessaires à la fiche de voyage.
    Version complète qui fait les mêmes appels API qu'odyssee-app.
    Gère à la fois les séjours et les excursions d'un jour.
    
    Args:
        form_data: Données du wizard (hotel_name, destination, prix, etc.)
        agency_config: Configuration de l'agence (clés API déchiffrées)
        
    Returns:
        Dictionnaire complet avec form_data, api_data enrichies, margin et savings
    """
    # Détecter le type de voyage
    is_day_trip = form_data.get('is_day_trip', False)
    
    if is_day_trip:
        return gather_day_trip_data(form_data, agency_config)
    
    # Pour les séjours classiques
    google_api_key = agency_config.get('google_api_key')
    
    if not google_api_key:
        print("⚠️ Aucune clé Google API - génération avec données limitées")
        return {
            'success': False,
            'error': 'Clé Google API manquante',
            'form_data': form_data,
            'api_data': {},
            'margin': 0,
            'savings': 0
        }
    
    # Créer le gatherer
    gatherer = TripDataGatherer(google_api_key)
    
    # Collecter les données
    hotel_name = form_data.get('hotel_name', '')
    destination = form_data.get('destination', '')
    
    api_data = gatherer.gather_all_data(hotel_name, destination)
    
    # Calculer les marges et économies
    hotel_b2b_price = int(form_data.get('hotel_b2b_price', 0) or 0)
    hotel_b2c_price = int(form_data.get('hotel_b2c_price', 0) or 0)
    pack_price = int(form_data.get('pack_price', 0) or 0)
    flight_price = int(form_data.get('flight_price', 0) or 0)
    transfer_cost = int(form_data.get('transfer_cost', 0) or 0)
    surcharge_cost = int(form_data.get('surcharge_cost', 0) or 0)
    car_rental_cost = int(form_data.get('car_rental_cost', 0) or 0)
    
    total_cost_b2b = hotel_b2b_price + flight_price + transfer_cost + surcharge_cost + car_rental_cost
    margin = pack_price - total_cost_b2b
    
    comparison_total = hotel_b2c_price + flight_price + transfer_cost + surcharge_cost + car_rental_cost
    savings = comparison_total - pack_price
    
    return {
        'success': True,
        'form_data': form_data,
        'api_data': api_data,
        'margin': margin,
        'savings': savings,
        'comparison_total': comparison_total
    }
