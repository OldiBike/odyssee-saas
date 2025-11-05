"""
Script de débogage pour l'API Hotels.com
Affiche les réponses brutes pour comprendre les problèmes
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')

def debug_autocomplete():
    """Debug de l'endpoint auto-complete"""
    
    print("\n" + "="*80)
    print("🔍 DEBUG AUTO-COMPLETE ENDPOINT")
    print("="*80)
    
    url = "https://hotels-com6.p.rapidapi.com/hotels/auto-complete"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
    }
    
    test_queries = ["Paris", "Rome", "London"]
    
    for query in test_queries:
        print(f"\n📍 Test pour: {query}")
        print(f"URL: {url}")
        print(f"Params: query={query}")
        
        try:
            response = requests.get(url, headers=headers, params={"query": query}, timeout=10)
            
            print(f"\n📊 Response Status: {response.status_code}")
            print(f"📊 Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"\n✅ JSON Response:")
                    print(json.dumps(data, indent=2)[:2000])  # Premiers 2000 chars
                except:
                    print(f"\n⚠️ Response Text (not JSON):")
                    print(response.text[:1000])
            elif response.status_code == 403:
                print(f"\n❌ ERREUR 403: Accès refusé")
                print(f"   Vérifiez que vous êtes abonné à l'API Hotels.com sur RapidAPI")
                print(f"   URL: https://rapidapi.com/apidojo/api/hotels-com6")
            else:
                print(f"\n❌ Erreur {response.status_code}")
                print(f"Response: {response.text[:500]}")
                
        except Exception as e:
            print(f"\n❌ Exception: {e}")


def debug_search():
    """Debug de l'endpoint search"""
    
    print("\n" + "="*80)
    print("🔍 DEBUG SEARCH ENDPOINT")
    print("="*80)
    
    url = "https://hotels-com6.p.rapidapi.com/hotels/search"
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
    }
    
    # Essayer avec un locationId connu (Paris = 2621)
    params = {
        "locationId": "2621",
        "rooms": json.dumps([{"adults": 2}]),
        "checkInDate": "2025-02-10",
        "checkOutDate": "2025-02-14",
        "currency": "EUR",
        "locale": "fr_FR"
    }
    
    print(f"\n📍 Test search pour Paris (locationId: 2621)")
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"\n✅ JSON Response Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                if isinstance(data, dict) and data.get('data'):
                    hotels = data['data'].get('hotels', [])
                    print(f"✅ Nombre d'hôtels: {len(hotels)}")
                    
                    if hotels:
                        print(f"\n🏨 Premier hôtel:")
                        print(json.dumps(hotels[0], indent=2)[:1000])
                else:
                    print(f"\n⚠️ Structure inattendue:")
                    print(json.dumps(data, indent=2)[:1000])
                    
            except:
                print(f"\n⚠️ Response Text (not JSON):")
                print(response.text[:1000])
        elif response.status_code == 403:
            print(f"\n❌ ERREUR 403: Accès refusé")
            print(f"   Vérifiez que vous êtes abonné à l'API Hotels.com sur RapidAPI")
        else:
            print(f"\n❌ Erreur {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")


def check_rapidapi_subscription():
    """Vérifie l'accès aux APIs RapidAPI"""
    
    print("\n" + "="*80)
    print("🔍 VÉRIFICATION DES ABONNEMENTS RAPIDAPI")
    print("="*80)
    
    apis_to_check = [
        ("Hotels.com", "hotels-com6.p.rapidapi.com", "/hotels/auto-complete?query=Paris"),
        ("Booking.com", "booking-com15.p.rapidapi.com", "/api/v1/hotels/searchDestination?query=Paris"),
        ("Sky Scrapper", "sky-scrapper.p.rapidapi.com", "/api/v2/flights/searchFlights?originSkyId=BRU&destinationSkyId=FCO&date=2025-02-10&returnDate=2025-02-14&adults=1&cabinClass=economy&currency=EUR&market=fr-BE&countryCode=BE")
    ]
    
    for api_name, host, endpoint in apis_to_check:
        print(f"\n{'='*80}")
        print(f"📡 Test: {api_name}")
        print(f"{'='*80}")
        
        url = f"https://{host}{endpoint}"
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": host
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ {api_name}: ACCESSIBLE")
            elif response.status_code == 403:
                print(f"❌ {api_name}: ACCÈS REFUSÉ (pas abonné ou quota dépassé)")
                print(f"   👉 Abonnez-vous sur: https://rapidapi.com")
            elif response.status_code == 429:
                print(f"⚠️ {api_name}: QUOTA DÉPASSÉ (trop de requêtes)")
            else:
                print(f"⚠️ {api_name}: Status {response.status_code}")
                
        except Exception as e:
            print(f"❌ {api_name}: ERREUR - {e}")


if __name__ == "__main__":
    if not RAPIDAPI_KEY:
        print("❌ RAPIDAPI_KEY manquante dans .env")
        exit(1)
    
    print(f"\n🔑 RAPIDAPI_KEY présente: {RAPIDAPI_KEY[:10]}...")
    
    # Vérifier les abonnements
    check_rapidapi_subscription()
    
    # Déboguer auto-complete
    debug_autocomplete()
    
    # Déboguer search
    debug_search()
    
    print("\n" + "="*80)
    print("✅ Débogage terminé")
    print("="*80)
