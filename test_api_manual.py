#!/usr/bin/env python3
"""
Script de test manuel des APIs pour débugger les problèmes
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')

def test_sky_scrapper():
    """Test Sky Scrapper API pour les vols"""
    print("\n" + "="*80)
    print("TEST 1: SKY SCRAPPER API (Vols)")
    print("="*80)
    
    url = "https://sky-scrapper.p.rapidapi.com/api/v2/flights/searchFlights"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "sky-scrapper.p.rapidapi.com"
    }
    
    params = {
        "originSkyId": "CRL",
        "destinationSkyId": "BCN",
        "originEntityId": "CRL",
        "destinationEntityId": "BCN",
        "date": "2025-12-01",
        "returnDate": "2025-12-04",
        "cabinClass": "economy",
        "adults": "2",
        "sortBy": "best",
        "currency": "EUR",
        "market": "fr-BE",
        "countryCode": "BE"
    }
    
    print(f"\n📤 URL: {url}")
    print(f"📤 Params: {json.dumps(params, indent=2)}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        print(f"\n✅ Status Code: {response.status_code}")
        print(f"📥 Response Headers: {dict(response.headers)}")
        
        data = response.json()
        print(f"\n📥 Response Body:")
        print(json.dumps(data, indent=2)[:2000])  # First 2000 chars
        
        # Analyze response
        if isinstance(data, dict):
            if data.get('status') == False:
                print(f"\n⚠️ API retourne status=false")
                print(f"Message: {data.get('message')}")
            elif data.get('data'):
                itineraries = data.get('data', {}).get('itineraries', [])
                print(f"\n✅ {len(itineraries)} itinéraires trouvés")
            else:
                print(f"\n⚠️ Pas de champ 'data' dans la réponse")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")


def test_booking_flights():
    """Test Booking.com Flights API"""
    print("\n" + "="*80)
    print("TEST 2: BOOKING.COM FLIGHTS API")
    print("="*80)
    
    url = "https://booking-com15.p.rapidapi.com/api/v1/flights/getMinPrice"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "booking-com15.p.rapidapi.com"
    }
    
    params = {
        "fromId": "CRL.AIRPORT",
        "toId": "BCN.AIRPORT",
        "departDate": "2025-12-01",
        "returnDate": "2025-12-04",
        "cabinClass": "ECONOMY",
        "currency_code": "EUR"
    }
    
    print(f"\n📤 URL: {url}")
    print(f"📤 Params: {json.dumps(params, indent=2)}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        print(f"\n✅ Status Code: {response.status_code}")
        
        data = response.json()
        print(f"\n📥 Response Body:")
        print(json.dumps(data, indent=2)[:2000])
        
        # Analyze dates
        if data.get('data'):
            results = data['data']
            print(f"\n✅ {len(results)} résultats trouvés")
            if results:
                first = results[0]
                print(f"\n📅 Premier résultat:")
                print(f"  Départ demandé: 2025-12-01")
                print(f"  Départ retourné: {first.get('departureDate')}")
                print(f"  Retour demandé: 2025-12-04")
                print(f"  Retour retourné: {first.get('returnDate')}")
                print(f"  Offset jours: {first.get('offsetDays')}")
                
    except Exception as e:
        print(f"\n❌ Erreur: {e}")


def test_hotels_autocomplete():
    """Test Hotels.com Auto-Complete"""
    print("\n" + "="*80)
    print("TEST 3: HOTELS.COM AUTO-COMPLETE")
    print("="*80)
    
    url = "https://hotels-com6.p.rapidapi.com/hotels/auto-complete"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
    }
    
    params = {"query": "Barcelona"}
    
    print(f"\n📤 URL: {url}")
    print(f"📤 Params: {json.dumps(params, indent=2)}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"\n✅ Status Code: {response.status_code}")
        
        data = response.json()
        print(f"\n📥 Response Body:")
        print(json.dumps(data, indent=2)[:2000])
        
        # Extract locationId
        if data.get('data'):
            suggestions = data['data'].get('sr', [])
            print(f"\n✅ {len(suggestions)} suggestions trouvées")
            if suggestions:
                for i, item in enumerate(suggestions[:3]):
                    print(f"\n  [{i+1}] {item.get('regionNames', {}).get('displayName', 'N/A')}")
                    print(f"      Type: {item.get('type')}")
                    print(f"      LocationID: {item.get('locationId')}")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")


def test_hotels_search():
    """Test Hotels.com Search"""
    print("\n" + "="*80)
    print("TEST 4: HOTELS.COM SEARCH")
    print("="*80)
    
    # First get Barcelona locationId
    location_id = "513"  # Barcelona from previous tests
    
    url = "https://hotels-com6.p.rapidapi.com/hotels/search"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
    }
    
    rooms_json = json.dumps([{"adults": 2}])
    
    params = {
        "locationId": location_id,
        "rooms": rooms_json,
        "checkinDate": "2025-12-01",
        "checkoutDate": "2025-12-04",
        "currency": "EUR",
        "locale": "fr_FR",
        "sort": "RECOMMENDED",
        "resultsSize": 50
    }
    
    print(f"\n📤 URL: {url}")
    print(f"📤 Params: {json.dumps(params, indent=2)}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        print(f"\n✅ Status Code: {response.status_code}")
        
        data = response.json()
        
        # Check structure
        if data.get('status') == False:
            print(f"\n⚠️ API retourne status=false")
            print(f"Message: {data.get('message')}")
            print(f"\n📥 Full Response:")
            print(json.dumps(data, indent=2)[:2000])
        else:
            property_listings = data.get('data', {}).get('propertySearchListings', [])
            
            print(f"\n✅ {len(property_listings)} listings retournés")
            
            # Filter only LodgingCard
            hotels = [item for item in property_listings if item.get('__typename') == 'LodgingCard']
            print(f"✅ {len(hotels)} hôtels (LodgingCard) après filtrage")
            
            # Show first 3 hotels with details
            for i, hotel in enumerate(hotels[:3]):
                print(f"\n  [{i+1}] {hotel.get('name', 'N/A')}")
                
                # Price
                price_info = hotel.get('price', {})
                total_price = price_info.get('total', 0)
                lead_price = price_info.get('lead', {}).get('amount', 0)
                print(f"      Prix total: {total_price}€")
                print(f"      Prix lead: {lead_price}€")
                
                # Rating
                rating_info = hotel.get('reviews', {})
                rating = rating_info.get('score', 0)
                count = rating_info.get('count', 0)
                print(f"      Note: {rating}/10 ({count} avis)")
                
                # Stars
                stars = hotel.get('star', 0)
                print(f"      Étoiles: {stars}")
                
                # Image
                images = hotel.get('images', [])
                print(f"      Images: {len(images)}")
                
            # Analyze rating distribution
            print(f"\n📊 Distribution des notes:")
            ratings = [hotel.get('reviews', {}).get('score', 0) for hotel in hotels]
            for threshold in [6, 7, 8, 9]:
                count = len([r for r in ratings if r >= threshold])
                print(f"  >= {threshold}/10: {count} hôtels")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🔍 TEST MANUEL DES APIs RAPIDAPI")
    print("="*80)
    
    if not RAPIDAPI_KEY:
        print("\n❌ RAPIDAPI_KEY non trouvée dans .env")
        return
    
    print(f"\n✅ RAPIDAPI_KEY trouvée: {RAPIDAPI_KEY[:10]}...")
    
    # Run tests
    test_sky_scrapper()
    test_booking_flights()
    test_hotels_autocomplete()
    test_hotels_search()
    
    print("\n" + "="*80)
    print("✅ Tests terminés")
    print("="*80)


if __name__ == "__main__":
    main()
