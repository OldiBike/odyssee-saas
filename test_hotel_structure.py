#!/usr/bin/env python3
"""
Script pour analyser la structure réelle des données Hotels.com
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')

def test_hotel_structure():
    """Voir la structure complète d'un hôtel"""
    
    url = "https://hotels-com6.p.rapidapi.com/hotels/search"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
    }
    
    rooms_json = json.dumps([{"adults": 2}])
    
    params = {
        "locationId": "513",  # Barcelona
        "rooms": rooms_json,
        "checkinDate": "2025-12-01",
        "checkoutDate": "2025-12-04",
        "currency": "EUR",
        "locale": "fr_FR",
        "sort": "RECOMMENDED",
        "resultsSize": 10
    }
    
    print("\n" + "="*80)
    print("ANALYSE STRUCTURE HOTELS.COM")
    print("="*80)
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        data = response.json()
        
        property_listings = data.get('data', {}).get('propertySearchListings', [])
        hotels = [item for item in property_listings if item.get('__typename') == 'LodgingCard']
        
        print(f"\n✅ {len(hotels)} hôtels trouvés")
        
        if hotels:
            # Afficher la structure COMPLÈTE du premier hôtel
            print(f"\n📋 STRUCTURE COMPLÈTE DU PREMIER HÔTEL:")
            print("="*80)
            print(json.dumps(hotels[0], indent=2, ensure_ascii=False))
            
            # Analyser les champs disponibles
            print(f"\n📊 CHAMPS DISPONIBLES (niveau racine):")
            print("="*80)
            for key in hotels[0].keys():
                value = hotels[0][key]
                value_type = type(value).__name__
                
                if isinstance(value, dict):
                    print(f"  • {key}: dict avec {len(value)} clés -> {list(value.keys())[:5]}")
                elif isinstance(value, list):
                    print(f"  • {key}: list avec {len(value)} items")
                else:
                    print(f"  • {key}: {value_type} = {str(value)[:50]}")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_hotel_structure()
