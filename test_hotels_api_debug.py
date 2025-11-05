#!/usr/bin/env python3
"""
Script de test pour debugger l'API Hotels.com
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')

def test_autocomplete(city_name):
    """Test de l'endpoint auto-complete"""
    url = "https://hotels-com6.p.rapidapi.com/hotels/auto-complete"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
    }
    
    params = {"query": city_name}
    
    print(f"\n{'='*60}")
    print(f"TEST AUTO-COMPLETE: '{city_name}'")
    print(f"{'='*60}")
    
    response = requests.get(url, headers=headers, params=params, timeout=10)
    data = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"\nRésultats trouvés:")
    
    if data and isinstance(data, dict):
        suggestions = data.get('data', {}).get('sr', [])
        
        for idx, item in enumerate(suggestions[:10], 1):  # Top 10
            region_names = item.get('regionNames', {})
            hierarchy = item.get('hierarchyInfo', {})
            
            print(f"\n{idx}. {region_names.get('displayName', 'N/A')}")
            print(f"   ID: {item.get('locationId')}")
            print(f"   Type: {item.get('type')}")
            print(f"   Pays: {hierarchy.get('country', {}).get('name', 'N/A')}")
            
    return data


def test_hotel_search(location_id, city_name):
    """Test de recherche d'hôtels"""
    url = "https://hotels-com6.p.rapidapi.com/hotels/search"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
    }
    
    params = {
        "locationId": location_id,
        "rooms": '[{"adults": 2}]',
        "checkinDate": "2025-12-01",
        "checkoutDate": "2025-12-04",
        "currency": "EUR",
        "locale": "fr_FR",
        "sort": "RECOMMENDED",
        "resultsSize": 10
    }
    
    print(f"\n{'='*60}")
    print(f"TEST RECHERCHE HÔTELS: {city_name} (ID: {location_id})")
    print(f"{'='*60}")
    
    response = requests.get(url, headers=headers, params=params, timeout=20)
    data = response.json()
    
    print(f"Status: {response.status_code}")
    
    if data.get('data', {}).get('hotels'):
        hotels = data['data']['hotels']
        print(f"\n✅ {len(hotels)} hôtels trouvés!")
        
        for idx, hotel in enumerate(hotels[:5], 1):
            print(f"\n{idx}. {hotel.get('name', 'N/A')}")
            print(f"   Prix: {hotel.get('price', {}).get('total', 'N/A')}€")
            print(f"   Note: {hotel.get('reviews', {}).get('score', 'N/A')}/10")
    else:
        print(f"\n❌ Aucun hôtel trouvé")
        print(f"Response: {json.dumps(data, indent=2)[:500]}")


if __name__ == "__main__":
    print("\n🔍 TEST API HOTELS.COM")
    print("="*60)
    
    # Test 1: Autocomplete Barcelone
    print("\n📍 TEST 1: Auto-complete 'Barcelone'")
    data_bcn = test_autocomplete("Barcelone")
    
    # Test 2: Autocomplete Barcelona (anglais)
    print("\n📍 TEST 2: Auto-complete 'Barcelona'")
    data_barcelona = test_autocomplete("Barcelona")
    
    # Test 3: Chercher des hôtels avec les IDs trouvés
    if data_barcelona:
        suggestions = data_barcelona.get('data', {}).get('sr', [])
        if suggestions:
            # Trouver Barcelona, Spain
            for item in suggestions:
                hierarchy = item.get('hierarchyInfo', {})
                country = hierarchy.get('country', {}).get('name', '')
                if country == 'Spain' or country == 'Espagne':
                    location_id = item.get('locationId')
                    print(f"\n✅ Trouvé Barcelona, Spain avec ID: {location_id}")
                    test_hotel_search(location_id, "Barcelona, Spain")
                    break
    
    print("\n" + "="*60)
    print("✅ Tests terminés")
