"""
Test des nouveaux endpoints Hotels.com
Vérifie que les 5 endpoints fonctionnent correctement avec des destinations réelles
"""

import os
import json
from dotenv import load_dotenv
from services.travel_inspector import TravelInspector

load_dotenv()

def test_hotel_endpoints():
    """Test complet des endpoints Hotels.com"""
    
    API_KEY = os.environ.get('GOOGLE_GEMINI_API_KEY')
    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
    
    if not RAPIDAPI_KEY:
        print("❌ Clé RAPIDAPI_KEY manquante dans .env")
        return False
    
    inspector = TravelInspector(API_KEY, RAPIDAPI_KEY)
    
    # Destinations de test
    test_cities = ["Paris", "Rome", "Barcelona", "London"]
    
    print("="*80)
    print("🧪 TEST DES ENDPOINTS HOTELS.COM")
    print("="*80)
    
    for city in test_cities:
        print(f"\n{'='*80}")
        print(f"📍 TEST: {city}")
        print(f"{'='*80}")
        
        # Test 1: Auto-complete
        print(f"\n1️⃣ Test Auto-Complete pour '{city}'")
        result = inspector._autocomplete_destination(city)
        if result:
            location_id = result.get('locationId')
            print(f"   ✅ LocationID: {location_id}")
            print(f"   ✅ Display: {result.get('display')}")
            print(f"   ✅ Type: {result.get('type')}")
            
            # Test 2: Filters
            print(f"\n2️⃣ Test Filters pour locationId {location_id}")
            filters = inspector._get_destination_filters(location_id)
            if filters:
                print(f"   ✅ Amenities disponibles: {len(filters.get('amenities', []))}")
                print(f"   ✅ Star ratings: {filters.get('star_ratings', [])}")
                print(f"   ✅ Quartiers: {len(filters.get('neighborhoods', []))}")
                
                # Afficher quelques exemples d'amenities
                if filters.get('amenities'):
                    print(f"\n   📋 Exemples d'équipements disponibles:")
                    for amenity in filters['amenities'][:5]:
                        print(f"      - {amenity.get('name', 'N/A')}")
            else:
                print(f"   ⚠️ Aucun filtre récupéré")
            
            # Test 3: Recherche d'hôtels pour obtenir un property_id
            print(f"\n3️⃣ Recherche d'hôtels à {city} (pour obtenir property_id)")
            try:
                from datetime import datetime, timedelta
                checkin = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                checkout = (datetime.now() + timedelta(days=34)).strftime('%Y-%m-%d')
                
                hotels = inspector._search_hotels_rapidapi(
                    destination=city,
                    checkin=checkin,
                    checkout=checkout,
                    adults=2,
                    max_price=200
                )
                
                if hotels:
                    print(f"   ✅ {len(hotels)} hôtels trouvés")
                    
                    # Prendre le premier hôtel pour tester les détails
                    test_hotel = hotels[0]
                    print(f"\n   🏨 Test des détails pour: {test_hotel['name']}")
                    
                    # Construire le property_id
                    # Note: La structure exacte du property_id peut varier selon l'API
                    # Essayons plusieurs formats
                    property_id_formats = [
                        f"{location_id}_{test_hotel.get('id', '')}",
                        str(test_hotel.get('id', '')),
                        f"{location_id}"
                    ]
                    
                    for property_id in property_id_formats:
                        if not property_id or property_id.endswith('_'):
                            continue
                            
                        print(f"\n   🔍 Test avec property_id: {property_id}")
                        
                        # Test 4: Hotel Highlights
                        print(f"   4️⃣ Test Highlights")
                        highlights = inspector._get_hotel_highlights(property_id)
                        if highlights:
                            print(f"      ✅ {len(highlights)} highlights trouvés:")
                            for highlight in highlights[:3]:
                                print(f"         - {highlight}")
                        else:
                            print(f"      ⚠️ Aucun highlight")
                        
                        # Test 5: Hotel Amenities
                        print(f"   5️⃣ Test Amenities")
                        amenities = inspector._get_hotel_amenities(property_id)
                        if amenities:
                            room = amenities.get('room_amenities', [])
                            hotel = amenities.get('hotel_amenities', [])
                            print(f"      ✅ Équipements chambre: {len(room)}")
                            print(f"      ✅ Équipements hôtel: {len(hotel)}")
                            if room:
                                print(f"         Exemples chambre: {room[:3]}")
                            if hotel:
                                print(f"         Exemples hôtel: {hotel[:3]}")
                        else:
                            print(f"      ⚠️ Aucun amenity")
                        
                        # Test 6: Hotel Location
                        print(f"   6️⃣ Test Location Details")
                        location = inspector._get_hotel_location_details(property_id)
                        if location:
                            coords = location.get('coordinates', {})
                            print(f"      ✅ Coordonnées: {coords}")
                            print(f"      ✅ Quartier: {location.get('neighborhood', 'N/A')}")
                            print(f"      ✅ Attractions: {len(location.get('nearby_attractions', []))}")
                        else:
                            print(f"      ⚠️ Aucune info de localisation")
                        
                        # Si on a trouvé au moins quelques infos, on arrête
                        if highlights or amenities or location:
                            print(f"\n   ✅ Format de property_id valide trouvé: {property_id}")
                            break
                    
                else:
                    print(f"   ⚠️ Aucun hôtel trouvé")
                    
            except Exception as e:
                print(f"   ❌ Erreur lors de la recherche: {e}")
        else:
            print(f"   ❌ Auto-complete a échoué pour '{city}'")
        
        print(f"\n{'='*80}\n")
    
    print("\n✅ Tests terminés!")
    print("\n📊 Résumé:")
    print("   • Auto-complete: Valide les destinations")
    print("   • Filters: Récupère les options de filtrage")
    print("   • Highlights: Points forts des hôtels")
    print("   • Amenities: Équipements détaillés")
    print("   • Location: Coordonnées et attractions")
    
    return True


if __name__ == "__main__":
    test_hotel_endpoints()
