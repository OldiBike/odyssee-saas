# services/api_gatherer.py
"""
Rassemble les données depuis les APIs externes (Google Places, YouTube, etc.)
pour enrichir les fiches de voyage.
"""

import requests
from typing import Dict, Any, List


def _get_place_details(place_id: str, api_key: str) -> Dict[str, Any]:
    """
    Récupère les détails d'un lieu depuis l'API Google Places.
    """
    if not place_id or not api_key:
        return {}

    url = 'https://maps.googleapis.com/maps/api/place/details/json'
    params = {
        'place_id': place_id,
        'fields': 'name,photos,rating,user_ratings_total,website,formatted_phone_number',
        'key': api_key,
        'language': 'fr'
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get('result', {})
    except requests.RequestException as e:
        print(f"❌ Erreur API Google Place Details: {e}")
        return {}


def _get_youtube_videos(query: str, api_key: str, max_results: int = 2) -> List[Dict[str, str]]:
    """
    Recherche des vidéos sur YouTube.
    """
    if not query or not api_key:
        return []

    url = 'https://www.googleapis.com/youtube/v3/search'
    params = {
        'part': 'snippet',
        'q': f"voyage {query}",
        'type': 'video',
        'videoEmbeddable': 'true',
        'key': api_key,
        'maxResults': max_results
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        videos = []
        for item in data.get('items', []):
            videos.append({
                'id': item['id']['videoId'],
                'title': item['snippet']['title'],
                'thumbnail': item['snippet']['thumbnails']['high']['url']
            })
        return videos
    except requests.RequestException as e:
        print(f"❌ Erreur API YouTube: {e}")
        return []


def gather_trip_data(form_data: Dict[str, Any], agency_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Point d'entrée pour collecter toutes les données nécessaires à la fiche de voyage.
    
    Args:
        form_data: Données du wizard (contient hotel_place_id, destination, etc.).
        agency_config: Configuration de l'agence (contient les clés API déchiffrées).
        
    Returns:
        Un dictionnaire contenant les données du formulaire et les données enrichies.
    """
    google_api_key = agency_config.get('google_api_key')
    youtube_api_key = agency_config.get('youtube_api_key')

    api_data = {
        'photos': [],
        'videos': [],
        'hotel_info': {},
        'destination_info': {}
    }

    # 1. Récupérer les informations de l'hôtel via Google Places
    hotel_place_id = form_data.get('hotel_place_id')
    if hotel_place_id and google_api_key:
        hotel_details = _get_place_details(hotel_place_id, google_api_key)
        if hotel_details:
            api_data['hotel_info'] = {
                'rating': hotel_details.get('rating'),
                'user_ratings_total': hotel_details.get('user_ratings_total'),
                'website': hotel_details.get('website'),
                'phone': hotel_details.get('formatted_phone_number')
            }
            
            # Extraire les URLs des photos
            photo_refs = [p['photo_reference'] for p in hotel_details.get('photos', [])]
            for ref in photo_refs[:6]: # Limiter à 6 photos
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=1200&photoreference={ref}&key={google_api_key}"
                api_data['photos'].append({'url': photo_url})

    # Si aucune photo d'hôtel, utiliser des placeholders
    if not api_data['photos']:
        api_data['photos'] = [
            {'url': f'https://via.placeholder.com/800x600?text={form_data.get("destination", "Voyage")}'}
        ]

    # 2. Récupérer des vidéos de la destination sur YouTube
    destination = form_data.get('destination')
    if destination and youtube_api_key:
        api_data['videos'] = _get_youtube_videos(destination, youtube_api_key)

    # 3. Calculer les marges (logique simple pour l'instant)
    pack_price = float(form_data.get('pack_price', 0))
    # On estime un coût B2B à 70% du prix de vente pour la démo
    total_b2b = pack_price * 0.7 
    margin = pack_price - total_b2b
    # On estime un prix public 15% plus cher que notre prix de vente
    total_b2c = pack_price * 1.15
    savings = total_b2c - pack_price

    return {
        'success': True,
        'form_data': form_data,
        'api_data': api_data,
        'margin': int(margin),
        'savings': int(savings)
    }