# 🌟 Système d'Inspiration de Voyages - Contexte & Phase 2

## 📋 Résumé de la fonctionnalité

Le système d'inspiration permet aux utilisateurs de décrire leur voyage idéal en langage naturel. L'IA analyse la demande, extrait les critères et propose 2-3 options concrètes de voyages avec vols et hôtels.

## 🏗️ Architecture actuelle (Phase 1 - MVP)

### Fichiers créés
1. **`services/travel_inspector.py`** - Service principal
   - Classe `TravelInspector` avec Gemini AI
   - Méthodes : `analyze_travel_request()`, `generate_travel_options()`, `search_and_aggregate()`
   - État : Génère des options simulées

2. **`templates/agency/inspiration.html`** - Interface utilisateur
   - Formulaire de recherche en langage naturel
   - Affichage des résultats en cards
   - Bouton "Utiliser ce voyage" pour pré-remplir le formulaire

3. **`INSPIRATION_VOYAGE_IMPLEMENTATION.md`** - Documentation technique

### Routes Flask (dans `app.py`)
```python
@app.route('/agency/inspiration')  # Page d'inspiration
@app.route('/api/inspire', methods=['POST'])  # API de recherche
```

### État actuel
- ✅ Interface complète et fonctionnelle
- ✅ Analyse IA des demandes (Gemini)
- ✅ Génération d'options simulées
- ⚠️ Gemini API nécessite activation dans Google Cloud Console
- 🔄 Prêt pour intégration APIs réelles

## 🔑 APIs & Clés pour Phase 2

### ✅ Déjà disponibles (fournies par l'utilisateur)

#### 1. Booking.com API (RapidAPI)
```python
url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"
headers = {
    "x-rapidapi-key": "bfded6814amshf70237b7208f148p143ee9jsn90a9ad24f875",
    "x-rapidapi-host": "booking-com15.p.rapidapi.com"
}
```

**Endpoints utiles :**
- `/api/v1/hotels/searchDestination` - Recherche de destinations
- `/api/v1/hotels/searchHotels` - Recherche d'hôtels
- `/api/v1/hotels/getHotelDetails` - Détails d'un hôtel

#### 2. Google Flights API (RapidAPI)
```python
url = "https://google-flights4.p.rapidapi.com/flights/search-roundtrip"
headers = {
    "x-rapidapi-key": "bfded6814amshf70237b7208f148p143ee9jsn90a9ad24f875",
    "x-rapidapi-host": "google-flights4.p.rapidapi.com"
}
```

**Endpoints utiles :**
- `/flights/search-roundtrip` - Recherche vols aller-retour
- `/flights/search-oneway` - Recherche vols aller simple

### ❓ Clés supplémentaires à demander

#### 3. Google Gemini API (**CRITIQUE**)
- **Statut** : Clé existe mais API pas activée dans le projet Google Cloud
- **Nécessaire pour** : Analyse des demandes en langage naturel
- **Action requise** :
  1. Activer "Generative Language API" : https://console.developers.google.com/apis/api/generativelanguage.googleapis.com/overview?project=1080042188681
  2. OU obtenir une nouvelle clé API : https://makersuite.google.com/app/apikey

#### 4. Mapping aéroports (Optionnel)
- **Objectif** : Convertir noms de villes en codes IATA (Rome → FCO, Bruxelles → BRU)
- **Options** :
  - API gratuite : https://www.back4app.com/database/back4app/list-of-all-continents-countries-cities/get-started/python/rest-api/requests
  - OU dictionnaire statique Python pour villes principales
  - OU API RapidAPI Airport Finder

## 🎯 Plan d'implémentation Phase 2

### Étape 1 : Configuration
1. Ajouter clés RapidAPI au fichier `.env`
2. Activer Gemini API dans Google Cloud
3. Créer dictionnaire de mapping villes → codes aéroports

### Étape 2 : Modifier `services/travel_inspector.py`

#### A. Ajouter méthodes d'API RapidAPI

```python
def _get_airport_code(self, city: str) -> str:
    """Convertit une ville en code IATA"""
    # Dictionnaire statique pour MVP
    airports = {
        'Rome': 'FCO',
        'Barcelone': 'BCN',
        'Lisbonne': 'LIS',
        'Venise': 'VCE',
        'Paris': 'CDG',
        'Madrid': 'MAD',
        # ... autres villes
    }
    return airports.get(city, 'FCO')  # Default Rome

def _search_hotels_rapidapi(self, destination, checkin, checkout, adults, max_price, stars=None):
    """Recherche d'hôtels via Booking.com RapidAPI"""
    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"
    
    headers = {
        "x-rapidapi-key": app.config['RAPIDAPI_KEY'],
        "x-rapidapi-host": "booking-com15.p.rapidapi.com"
    }
    
    params = {
        "dest_id": destination,
        "search_type": "CITY",
        "arrival_date": checkin,
        "departure_date": checkout,
        "adults": adults,
        "room_qty": 1,
        "price_min": 0,
        "price_max": max_price,
        "order_by": "price",
        "filter_by_currency": "EUR",
        "languagecode": "fr"
    }
    
    if stars:
        params["categories_filter"] = f"class::{stars}"
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Parser les résultats
        hotels = []
        for hotel in data.get('result', [])[:5]:  # Top 5 hôtels
            hotels.append({
                'name': hotel.get('hotel_name'),
                'stars': hotel.get('class'),
                'price': hotel.get('min_total_price'),
                'image': hotel.get('main_photo_url'),
                'rating': hotel.get('review_score'),
                'address': hotel.get('address')
            })
        
        return hotels
        
    except Exception as e:
        logger.error(f"Erreur API Booking: {e}")
        return []

def _search_flights_rapidapi(self, origin, destination, departure_date, return_date, adults):
    """Recherche de vols via Google Flights RapidAPI"""
    url = "https://google-flights4.p.rapidapi.com/flights/search-roundtrip"
    
    headers = {
        "x-rapidapi-key": app.config['RAPIDAPI_KEY'],
        "x-rapidapi-host": "google-flights4.p.rapidapi.com"
    }
    
    params = {
        "departureId": origin,
        "arrivalId": destination,
        "outboundDate": departure_date,
        "returnDate": return_date,
        "adults": adults,
        "currency": "EUR",
        "language": "fr"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Parser les résultats
        flights = []
        for flight in data.get('flights', [])[:5]:  # Top 5 vols
            flights.append({
                'airline': flight.get('airline'),
                'price': flight.get('price'),
                'departure_time': flight.get('departure_time'),
                'arrival_time': flight.get('arrival_time'),
                'duration': flight.get('duration'),
                'stops': flight.get('stops', 0)
            })
        
        return flights
        
    except Exception as e:
        logger.error(f"Erreur API Google Flights: {e}")
        return []
```

#### B. Remplacer `generate_travel_options()`

```python
def generate_travel_options(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Génère 2-3 options de voyage basées sur les critères
    AVEC APIs réelles
    """
    
    destination = criteria.get('destination')
    budget = criteria.get('budget_pp', 500)
    date_debut = criteria.get('date_debut')
    date_fin = criteria.get('date_fin')
    num_personnes = criteria.get('num_personnes', 2)
    inclusions = criteria.get('inclusions', [])
    stars_min = criteria.get('stars_min')
    
    # Dates par défaut si non fournies
    if not date_debut:
        date_debut = self._get_default_date()
    if not date_fin:
        date_fin = self._get_default_date(days=4)
    
    # 1. Rechercher vols
    origin_code = 'BRU'  # Bruxelles par défaut
    dest_code = self._get_airport_code(destination)
    
    flights = self._search_flights_rapidapi(
        origin=origin_code,
        destination=dest_code,
        departure_date=date_debut,
        return_date=date_fin,
        adults=num_personnes
    )
    
    # 2. Rechercher hôtels
    hotels = self._search_hotels_rapidapi(
        destination=destination,
        checkin=date_debut,
        checkout=date_fin,
        adults=num_personnes,
        max_price=budget * 0.7,  # 70% du budget pour l'hôtel
        stars=stars_min
    )
    
    # 3. Combiner pour créer des options
    options = []
    
    for i, hotel in enumerate(hotels[:3]):
        # Prendre le vol correspondant (ou le moins cher)
        flight = flights[min(i, len(flights)-1)] if flights else None
        
        if flight:
            total_price = (hotel['price'] + flight['price']) // num_personnes
            
            # Vérifier si dans le budget
            if total_price <= budget * 1.1:  # Tolérance de 10%
                options.append({
                    'destination': destination,
                    'date_debut': date_debut,
                    'date_fin': date_fin,
                    'total_price': total_price,
                    'hotel': hotel,
                    'flight': flight,
                    'inclusions': inclusions,
                    'option_type': 'real_data'
                })
    
    # Si pas assez d'options réelles, compléter avec simulées
    while len(options) < 2:
        options.append(self._generate_fallback_option(criteria, len(options)))
    
    return options[:3]  # Max 3 options
```

### Étape 3 : Configuration `.env`

Ajouter ces lignes au fichier `.env` :

```bash
# RapidAPI (déjà fourni)
RAPIDAPI_KEY=bfded6814amshf70237b7208f148p143ee9jsn90a9ad24f875

# Google Gemini (à activer)
GOOGLE_GEMINI_API_KEY=votre_clé_gemini_ici
```

### Étape 4 : Mise à jour `config.py`

```python
class Config:
    # ... autres configs
    
    # RapidAPI
    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
    RAPIDAPI_BOOKING_HOST = 'booking-com15.p.rapidapi.com'
    RAPIDAPI_FLIGHTS_HOST = 'google-flights4.p.rapidapi.com'
```

## 📊 Exemple de flux Phase 2

```
Utilisateur : "4 jours à Rome, budget 400€ par personne"
    ↓
Gemini AI extrait :
    - destination: "Rome"
    - budget_pp: 400
    - num_personnes: 2
    ↓
1. Appel Google Flights API
   BRU → FCO (dates flexibles)
   → Retourne 5 options de vols
    ↓
2. Appel Booking.com API
   Rome, 4 jours, max 280€ (70% du budget)
   → Retourne 5 hôtels
    ↓
3. Combinaison intelligente
   Pour chaque hôtel, associer un vol
   Filtrer par budget total (≤ 400€)
    ↓
4. Résultat : 2-3 options réelles
   Option 1: Hotel Central (240€) + Brussels Airlines (140€) = 380€
   Option 2: Grand Hotel (260€) + Ryanair (120€) = 380€
   Option 3: Luxury Resort (300€) + Brussels Airlines (140€) = 440€ (10% au-dessus)
```

## 🔧 Checklist Phase 2

### Configuration
- [ ] Activer Gemini API dans Google Cloud Console
- [ ] Ajouter `RAPIDAPI_KEY` au `.env`
- [ ] Vérifier `GOOGLE_GEMINI_API_KEY` dans `.env`
- [ ] Mettre à jour `config.py` avec nouvelles configs

### Code
- [ ] Créer dictionnaire de mapping villes → codes IATA
- [ ] Implémenter `_search_hotels_rapidapi()`
- [ ] Implémenter `_search_flights_rapidapi()`
- [ ] Remplacer `generate_travel_options()` avec vraies APIs
- [ ] Ajouter gestion des erreurs API
- [ ] Implémenter fallback si APIs échouent

### Tests
- [ ] Tester recherche d'hôtels
- [ ] Tester recherche de vols
- [ ] Tester combinaison des résultats
- [ ] Vérifier respect du budget
- [ ] Tester avec différentes destinations

### Optimisations
- [ ] Ajouter système de cache (Redis) pour limiter appels API
- [ ] Implémenter pagination des résultats
- [ ] Ajouter filtres avancés (stops, compagnies, etc.)

## 🚨 Points d'attention

### 1. Rate Limiting RapidAPI
- Plan gratuit : ~500 requêtes/mois
- Implémenter un cache pour éviter appels répétés
- Monitorer l'usage dans le dashboard RapidAPI

### 2. Coûts
- RapidAPI Booking.com : Gratuit jusqu'à 500 req/mois
- Google Flights : Gratuit jusqu'à 500 req/mois
- Gemini API : Gratuit jusqu'à 60 req/min

### 3. Erreurs courantes
- **404 Hotel** : Destination ID invalide → Fallback sur données simulées
- **429 Too Many Requests** : Rate limit atteint → Utiliser cache
- **503 Service Unavailable** : API temporairement down → Afficher message utilisateur

## 📝 Variables d'environnement nécessaires

```bash
# === EXISTANTES ===
GOOGLE_PLACES_API_KEY=votre_clé_ici  # Pour autocomplete

# === À AJOUTER ===
GOOGLE_GEMINI_API_KEY=votre_nouvelle_clé_gemini  # Pour IA
RAPIDAPI_KEY=bfded6814amshf70237b7208f148p143ee9jsn90a9ad24f875  # Déjà fourni
```

## 🎯 Prochaines étapes

1. **Activer Gemini API** 
   - Aller sur : https://console.developers.google.com/apis/api/generativelanguage.googleapis.com/overview?project=1080042188681
   - Cliquer "Activer"
   - Attendre 2-3 minutes

2. **Tester les APIs RapidAPI**
   - Faire quelques appels de test
   - Vérifier les formats de réponse
   - Ajuster le parsing si nécessaire

3. **Implémenter Phase 2**
   - Suivre la checklist ci-dessus
   - Tester progressivement chaque fonction
   - Déployer en production

## 📖 Documentation API

### Booking.com API
- **Doc** : https://rapidapi.com/DataCrawler/api/booking-com15
- **Endpoints utiles** :
  - `searchDestination` : Trouver ID de destination
  - `searchHotels` : Rechercher hôtels
  - `getHotelDetails` : Détails complets

### Google Flights API
- **Doc** : https://rapidapi.com/ar.farooqi/api/google-flights4
- **Endpoints** :
  - `search-roundtrip` : Vols aller-retour
  - `search-oneway` : Vols aller simple

---

**Dernière mise à jour** : 11/01/2025  
**Statut** : Phase 1 (MVP) complète, Phase 2 prête à implémenter  
**Auteur** : Cline AI
