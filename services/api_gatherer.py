# services/api_gatherer.py
"""
Service pour collecter et enrichir les données de voyage
via les APIs externes (Google Places, YouTube, etc.)
"""

import requests
import json
from typing import Dict, Any, List, Optional
import re
from datetime import datetime

class APIGatherer:
    """Collecteur de données depuis les APIs externes"""
    
    def __init__(self, google_api_key: str = None, youtube_api_key: str = None):
        """
        Initialise le collecteur avec les clés API
        
        Args:
            google_api_key: Clé API Google Places
            youtube_api_key: Clé API YouTube
        """
        self.google_api_key = google_api_key
        self.youtube_api_key = youtube_api_key
        self.session = requests.Session()
    
    def gather_trip_data(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collecte toutes les données enrichies pour un voyage
        
        Args:
            form_data: Données du formulaire/wizard
            
        Returns:
            Dict avec toutes les données enrichies
        """
        
        destination = form_data.get('destination', '')
        hotel_name = form_data.get('hotel_name', '')
        activities = form_data.get('activities', [])
        
        result = {
            'success': True,
            'form_data': form_data,
            'api_data': {
                'destination_info': {},
                'hotel_info': {},
                'photos': [],
                'videos': [],
                'attractions': [],
                'weather': {},
                'reviews_summary': {}
            },
            'enrichment_errors': []
        }
        
        try:
            # 1. Rechercher les informations sur la destination
            if destination:
                dest_info = self._get_destination_info(destination)
                if dest_info:
                    result['api_data']['destination_info'] = dest_info
                    
                    # Récupérer les photos de la destination
                    if dest_info.get('place_id'):
                        photos = self._get_place_photos(dest_info['place_id'])
                        result['api_data']['photos'].extend(photos[:3])
            
            # 2. Rechercher les informations sur l'hôtel
            if hotel_name and destination:
                hotel_info = self._search_hotel(hotel_name, destination)
                if hotel_info:
                    result['api_data']['hotel_info'] = hotel_info
                    
                    # Ajouter les photos de l'hôtel
                    if hotel_info.get('place_id'):
                        hotel_photos = self._get_place_photos(hotel_info['place_id'])
                        result['api_data']['photos'].extend(hotel_photos[:3])
            
            # 3. Rechercher les attractions touristiques
            if destination:
                attractions = self._get_nearby_attractions(destination, activities)
                result['api_data']['attractions'] = attractions
            
            # 4. Rechercher des vidéos YouTube
            if destination and self.youtube_api_key:
                videos = self._search_youtube_videos(destination, hotel_name)
                result['api_data']['videos'] = videos[:3]
            
            # 5. Générer un résumé des avis (simulé pour l'instant)
            result['api_data']['reviews_summary'] = self._generate_reviews_summary(
                hotel_info if hotel_info else dest_info
            )
            
            # 6. Calculer les marges et économies
            result.update(self._calculate_pricing(form_data))
            
        except Exception as e:
            print(f"❌ Erreur lors de la collecte des données: {e}")
            result['enrichment_errors'].append(str(e))
        
        return result
    
    def _get_destination_info(self, destination: str) -> Optional[Dict]:
        """
        Récupère les informations sur une destination via Google Places
        
        Args:
            destination: Nom de la destination
            
        Returns:
            Dict avec les infos ou None
        """
        if not self.google_api_key:
            return None
        
        try:
            # Recherche de la destination
            search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
            params = {
                'input': destination,
                'inputtype': 'textquery',
                'fields': 'place_id,name,formatted_address,geometry,types,rating,user_ratings_total',
                'language': 'fr',
                'key': self.google_api_key
            }
            
            response = self.session.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('candidates'):
                    place = data['candidates'][0]
                    
                    # Récupérer plus de détails
                    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                    details_params = {
                        'place_id': place['place_id'],
                        'fields': 'name,formatted_address,geometry,photos,rating,user_ratings_total,types,website,formatted_phone_number,opening_hours,price_level',
                        'language': 'fr',
                        'key': self.google_api_key
                    }
                    
                    details_response = self.session.get(details_url, params=details_params, timeout=10)
                    
                    if details_response.status_code == 200:
                        details = details_response.json().get('result', {})
                        
                        return {
                            'place_id': place['place_id'],
                            'name': details.get('name', destination),
                            'address': details.get('formatted_address', ''),
                            'coordinates': details.get('geometry', {}).get('location', {}),
                            'rating': details.get('rating', 0),
                            'total_reviews': details.get('user_ratings_total', 0),
                            'photos': details.get('photos', [])[:5],
                            'types': details.get('types', []),
                            'website': details.get('website'),
                            'phone': details.get('formatted_phone_number'),
                            'price_level': details.get('price_level', 0)
                        }
            
        except Exception as e:
            print(f"❌ Erreur Google Places API: {e}")
        
        return None
    
    def _search_hotel(self, hotel_name: str, destination: str) -> Optional[Dict]:
        """
        Recherche un hôtel spécifique
        
        Args:
            hotel_name: Nom de l'hôtel
            destination: Ville/destination
            
        Returns:
            Dict avec les infos de l'hôtel ou None
        """
        if not self.google_api_key or not hotel_name:
            return None
        
        try:
            # Recherche de l'hôtel
            search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            params = {
                'query': f"{hotel_name} hotel {destination}",
                'type': 'lodging',
                'language': 'fr',
                'key': self.google_api_key
            }
            
            response = self.session.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    hotel = data['results'][0]
                    
                    return {
                        'place_id': hotel.get('place_id'),
                        'name': hotel.get('name'),
                        'address': hotel.get('formatted_address'),
                        'rating': hotel.get('rating', 0),
                        'total_reviews': hotel.get('user_ratings_total', 0),
                        'price_level': hotel.get('price_level', 0),
                        'photos': hotel.get('photos', [])[:5],
                        'types': hotel.get('types', [])
                    }
        
        except Exception as e:
            print(f"❌ Erreur recherche hôtel: {e}")
        
        return None
    
    def _get_place_photos(self, place_id: str, max_photos: int = 5) -> List[Dict]:
        """
        Récupère les URLs des photos d'un lieu
        
        Args:
            place_id: ID du lieu Google
            max_photos: Nombre maximum de photos
            
        Returns:
            Liste des URLs de photos
        """
        if not self.google_api_key or not place_id:
            return []
        
        photos = []
        
        try:
            # Récupérer les détails du lieu pour obtenir les références des photos
            details_url = "https://maps.googleapis.com/maps/api/place/details/json"
            params = {
                'place_id': place_id,
                'fields': 'photos',
                'key': self.google_api_key
            }
            
            response = self.session.get(details_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                photo_refs = data.get('result', {}).get('photos', [])[:max_photos]
                
                for photo in photo_refs:
                    photo_url = self._build_photo_url(photo.get('photo_reference'))
                    if photo_url:
                        photos.append({
                            'url': photo_url,
                            'width': photo.get('width', 800),
                            'height': photo.get('height', 600),
                            'attributions': photo.get('html_attributions', [])
                        })
        
        except Exception as e:
            print(f"❌ Erreur récupération photos: {e}")
        
        return photos
    
    def _build_photo_url(self, photo_reference: str, max_width: int = 800) -> Optional[str]:
        """
        Construit l'URL d'une photo Google Places
        
        Args:
            photo_reference: Référence de la photo
            max_width: Largeur maximum
            
        Returns:
            URL de la photo
        """
        if not photo_reference or not self.google_api_key:
            return None
        
        return (
            f"https://maps.googleapis.com/maps/api/place/photo"
            f"?maxwidth={max_width}"
            f"&photoreference={photo_reference}"
            f"&key={self.google_api_key}"
        )
    
    def _get_nearby_attractions(self, destination: str, 
                                activities: List[str] = None,
                                max_results: int = 10) -> List[Dict]:
        """
        Recherche les attractions touristiques à proximité
        
        Args:
            destination: Destination
            activities: Liste d'activités spécifiques
            max_results: Nombre maximum de résultats
            
        Returns:
            Liste des attractions
        """
        if not self.google_api_key:
            return []
        
        attractions = []
        
        try:
            # D'abord, obtenir les coordonnées de la destination
            dest_info = self._get_destination_info(destination)
            if not dest_info or not dest_info.get('coordinates'):
                return []
            
            lat = dest_info['coordinates'].get('lat')
            lng = dest_info['coordinates'].get('lng')
            
            # Recherche des attractions à proximité
            nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'location': f"{lat},{lng}",
                'radius': 5000,  # 5km
                'type': 'tourist_attraction',
                'language': 'fr',
                'key': self.google_api_key
            }
            
            response = self.session.get(nearby_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])[:max_results]
                
                for place in results:
                    attraction = {
                        'name': place.get('name'),
                        'place_id': place.get('place_id'),
                        'rating': place.get('rating', 0),
                        'total_reviews': place.get('user_ratings_total', 0),
                        'vicinity': place.get('vicinity'),
                        'types': place.get('types', []),
                        'photo_url': None
                    }
                    
                    # Ajouter la première photo si disponible
                    if place.get('photos'):
                        photo_ref = place['photos'][0].get('photo_reference')
                        if photo_ref:
                            attraction['photo_url'] = self._build_photo_url(photo_ref, 400)
                    
                    attractions.append(attraction)
            
            # Si des activités spécifiques sont mentionnées, les rechercher
            if activities:
                for activity in activities[:3]:  # Limiter à 3 activités
                    specific_attraction = self._search_specific_attraction(activity, destination)
                    if specific_attraction and specific_attraction not in attractions:
                        attractions.insert(0, specific_attraction)
        
        except Exception as e:
            print(f"❌ Erreur recherche attractions: {e}")
        
        return attractions
    
    def _search_specific_attraction(self, activity: str, destination: str) -> Optional[Dict]:
        """
        Recherche une attraction spécifique
        
        Args:
            activity: Nom de l'activité/attraction
            destination: Destination
            
        Returns:
            Dict avec les infos de l'attraction
        """
        if not self.google_api_key:
            return None
        
        try:
            search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            params = {
                'query': f"{activity} {destination}",
                'language': 'fr',
                'key': self.google_api_key
            }
            
            response = self.session.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    place = data['results'][0]
                    
                    attraction = {
                        'name': place.get('name'),
                        'place_id': place.get('place_id'),
                        'rating': place.get('rating', 0),
                        'total_reviews': place.get('user_ratings_total', 0),
                        'address': place.get('formatted_address'),
                        'types': place.get('types', []),
                        'photo_url': None
                    }
                    
                    if place.get('photos'):
                        photo_ref = place['photos'][0].get('photo_reference')
                        if photo_ref:
                            attraction['photo_url'] = self._build_photo_url(photo_ref, 400)
                    
                    return attraction
        
        except Exception as e:
            print(f"❌ Erreur recherche activité spécifique: {e}")
        
        return None
    
    def _search_youtube_videos(self, destination: str, 
                               hotel_name: str = None,
                               max_results: int = 5) -> List[Dict]:
        """
        Recherche des vidéos YouTube sur la destination
        
        Args:
            destination: Destination
            hotel_name: Nom de l'hôtel (optionnel)
            max_results: Nombre maximum de vidéos
            
        Returns:
            Liste des vidéos
        """
        if not self.youtube_api_key:
            return []
        
        videos = []
        
        try:
            # Construire la requête de recherche
            search_query = f"{destination} voyage tourisme"
            if hotel_name:
                search_query = f"{hotel_name} {destination}"
            
            # API YouTube Data v3
            search_url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                'part': 'snippet',
                'q': search_query,
                'type': 'video',
                'videoEmbeddable': 'true',
                'videoDuration': 'short',  # Vidéos courtes
                'maxResults': max_results,
                'order': 'relevance',
                'regionCode': 'FR',
                'relevanceLanguage': 'fr',
                'key': self.youtube_api_key
            }
            
            response = self.session.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data.get('items', []):
                    snippet = item.get('snippet', {})
                    video = {
                        'id': item.get('id', {}).get('videoId'),
                        'title': snippet.get('title'),
                        'description': snippet.get('description', '')[:200],
                        'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url'),
                        'channel': snippet.get('channelTitle'),
                        'published_at': snippet.get('publishedAt'),
                        'embed_url': f"https://www.youtube.com/embed/{item.get('id', {}).get('videoId')}"
                    }
                    videos.append(video)
        
        except Exception as e:
            print(f"❌ Erreur YouTube API: {e}")
        
        return videos
    
    def _generate_reviews_summary(self, place_info: Optional[Dict]) -> Dict:
        """
        Génère un résumé des avis (simulé ou basé sur les données Google)
        
        Args:
            place_info: Informations du lieu
            
        Returns:
            Résumé des avis
        """
        if not place_info:
            return {
                'average_rating': 4.2,
                'total_reviews': 0,
                'rating_distribution': {
                    5: 0,
                    4: 0,
                    3: 0,
                    2: 0,
                    1: 0
                },
                'highlights': []
            }
        
        rating = place_info.get('rating', 4.2)
        total_reviews = place_info.get('total_reviews', 0)
        
        # Simuler une distribution des notes (en production, utiliser de vraies données)
        distribution = self._simulate_rating_distribution(rating, total_reviews)
        
        # Générer des points forts basés sur le rating
        highlights = self._generate_highlights(rating)
        
        return {
            'average_rating': rating,
            'total_reviews': total_reviews,
            'rating_distribution': distribution,
            'highlights': highlights
        }
    
    def _simulate_rating_distribution(self, average_rating: float, 
                                      total_reviews: int) -> Dict[int, int]:
        """
        Simule une distribution réaliste des notes
        
        Args:
            average_rating: Note moyenne
            total_reviews: Nombre total d'avis
            
        Returns:
            Distribution des notes
        """
        if total_reviews == 0:
            return {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        
        # Algorithme simple pour distribuer les notes
        distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        
        if average_rating >= 4.5:
            distribution[5] = int(total_reviews * 0.6)
            distribution[4] = int(total_reviews * 0.25)
            distribution[3] = int(total_reviews * 0.10)
            distribution[2] = int(total_reviews * 0.03)
            distribution[1] = int(total_reviews * 0.02)
        elif average_rating >= 4.0:
            distribution[5] = int(total_reviews * 0.35)
            distribution[4] = int(total_reviews * 0.40)
            distribution[3] = int(total_reviews * 0.15)
            distribution[2] = int(total_reviews * 0.07)
            distribution[1] = int(total_reviews * 0.03)
        elif average_rating >= 3.5:
            distribution[5] = int(total_reviews * 0.20)
            distribution[4] = int(total_reviews * 0.30)
            distribution[3] = int(total_reviews * 0.30)
            distribution[2] = int(total_reviews * 0.15)
            distribution[1] = int(total_reviews * 0.05)
        else:
            distribution[5] = int(total_reviews * 0.10)
            distribution[4] = int(total_reviews * 0.20)
            distribution[3] = int(total_reviews * 0.30)
            distribution[2] = int(total_reviews * 0.25)
            distribution[1] = int(total_reviews * 0.15)
        
        # Ajuster pour que le total soit exact
        diff = total_reviews - sum(distribution.values())
        if diff > 0:
            distribution[4] += diff
        
        return distribution
    
    def _generate_highlights(self, rating: float) -> List[str]:
        """
        Génère des points forts basés sur le rating
        
        Args:
            rating: Note moyenne
            
        Returns:
            Liste de points forts
        """
        if rating >= 4.5:
            return [
                "🌟 Exceptionnel selon les voyageurs",
                "📍 Emplacement idéal",
                "👨‍💼 Personnel très professionnel",
                "✨ Propreté irréprochable"
            ]
        elif rating >= 4.0:
            return [
                "👍 Très bien noté",
                "📍 Bon emplacement",
                "🛏️ Confort apprécié",
                "💰 Bon rapport qualité-prix"
            ]
        elif rating >= 3.5:
            return [
                "✓ Correct dans l'ensemble",
                "📍 Emplacement convenable",
                "💰 Prix raisonnable"
            ]
        else:
            return [
                "💰 Prix économique",
                "📍 Localisation pratique"
            ]
    
    def _calculate_pricing(self, form_data: Dict) -> Dict:
        """
        Calcule les marges et économies
        
        Args:
            form_data: Données du formulaire
            
        Returns:
            Dict avec margin et savings
        """
        try:
            # Extraire les prix
            pack_price = float(form_data.get('pack_price', 0))
            
            # Prix B2B (coûts réels)
            hotel_b2b = float(form_data.get('hotel_b2b_price', 0))
            flight = float(form_data.get('flight_price', 0))
            transfer = float(form_data.get('transfer_cost', 0))
            car = float(form_data.get('car_rental_cost', 0))
            surcharge = float(form_data.get('surcharge_cost', 0))
            
            # Prix B2C (prix publics)
            hotel_b2c = float(form_data.get('hotel_b2c_price', hotel_b2b * 1.3))
            
            # Calculs
            total_b2b = hotel_b2b + flight + transfer + car + surcharge
            total_b2c = hotel_b2c + flight + transfer + car + surcharge
            
            margin = pack_price - total_b2b
            savings = total_b2c - pack_price
            
            # Pourcentages
            margin_percentage = (margin / pack_price * 100) if pack_price > 0 else 0
            savings_percentage = (savings / total_b2c * 100) if total_b2c > 0 else 0
            
            return {
                'margin': round(margin, 2),
                'margin_percentage': round(margin_percentage, 1),
                'savings': round(max(0, savings), 2),
                'savings_percentage': round(max(0, savings_percentage), 1),
                'total_b2b': round(total_b2b, 2),
                'total_b2c': round(total_b2c, 2)
            }
            
        except (ValueError, TypeError) as e:
            print(f"❌ Erreur calcul pricing: {e}")
            return {
                'margin': 0,
                'margin_percentage': 0,
                'savings': 0,
                'savings_percentage': 0,
                'total_b2b': 0,
                'total_b2c': 0
            }


# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================

def gather_trip_data(form_data: Dict[str, Any], agency_config: Dict[str, str]) -> Dict[str, Any]:
    """
    Point d'entrée pour collecter les données d'un voyage
    
    Args:
        form_data: Données du formulaire/wizard
        agency_config: Configuration de l'agence (clés API déchiffrées)
        
    Returns:
        Données enrichies du voyage
    """
    gatherer = APIGatherer(
        google_api_key=agency_config.get('google_api_key'),
        youtube_api_key=agency_config.get('youtube_api_key')
    )
    
    return gatherer.gather_trip_data(form_data)


def enrich_destination_data(destination: str, google_api_key: str) -> Dict[str, Any]:
    """
    Enrichit uniquement les données d'une destination
    
    Args:
        destination: Nom de la destination
        google_api_key: Clé API Google
        
    Returns:
        Données enrichies de la destination
    """
    gatherer = APIGatherer(google_api_key=google_api_key)
    
    dest_info = gatherer._get_destination_info(destination)
    attractions = gatherer._get_nearby_attractions(destination)
    
    return {
        'destination_info': dest_info,
        'attractions': attractions
    }


# ==============================================================================
# TESTS
# ==============================================================================

if __name__ == "__main__":
    """
    Tests du service API Gatherer
    Lancez : python services/api_gatherer.py
    """
    
    import os
    
    # Clés API depuis l'environnement
    GOOGLE_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY')
    YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
    
    if not GOOGLE_API_KEY:
        print("❌ Clé GOOGLE_PLACES_API_KEY manquante dans .env")
        exit(1)
    
    print("\n" + "="*60)
    print("TEST API GATHERER")
    print("="*60)
    
    # Données de test
    test_form_data = {
        'destination': 'Rome, Italie',
        'hotel_name': 'Hotel Colosseo',
        'activities': ['Colisée', 'Vatican', 'Fontaine de Trevi'],
        'pack_price': 500,
        'hotel_b2b_price': 200,
        'hotel_b2c_price': 300,
        'flight_price': 150,
        'transfer_cost': 50,
        'car_rental_cost': 0,
        'surcharge_cost': 20
    }
    
    # Configuration d'agence simulée
    agency_config = {
        'google_api_key': GOOGLE_API_KEY,
        'youtube_api_key': YOUTUBE_API_KEY
    }
    
    # Test de collecte
    print("\n📊 Test de collecte de données pour Rome...")
    result = gather_trip_data(test_form_data, agency_config)
    
    if result['success']:
        print("\n✅ Collecte réussie !")
        print(f"   - Destination: {result['api_data']['destination_info'].get('name', 'N/A')}")
        print(f"   - Photos trouvées: {len(result['api_data']['photos'])}")
        print(f"   - Attractions trouvées: {len(result['api_data']['attractions'])}")
        print(f"   - Vidéos trouvées: {len(result['api_data']['videos'])}")
        print(f"   - Marge calculée: {result['margin']}€ ({result['margin_percentage']}%)")
        print(f"   - Économies client: {result['savings']}€")
        
        # Afficher quelques attractions
        if result['api_data']['attractions']:
            print("\n🎯 Top 3 attractions:")
            for att in result['api_data']['attractions'][:3]:
                print(f"   - {att['name']} (⭐ {att['rating']})")
    else:
        print("❌ Échec de la collecte")
        print(f"   Erreurs: {result.get('enrichment_errors', [])}")
    
    print("\n✅ Tests terminés !")