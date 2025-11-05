# 🛫 Endpoints Google Flights pour l'Onglet Inspiration

## 📸 Analyse de la Capture d'Écran

**API visible** : `google-flights2.p.rapidapi.com`  
**Clé RapidAPI** : `bfded6814amshf70237b7208f148p143ee9jsn90a9ad24f875`

## ✅ Endpoints NÉCESSAIRES pour l'Inspiration

### 1. **Search Flights** (GET) - PRIORITAIRE ⭐⭐⭐

**Endpoint** : `/api/v1/searchFlights`

**Pourquoi ?**
- Endpoint principal pour rechercher des vols aller-retour
- Retourne les options de vols avec prix, durée, compagnies
- Correspond exactement au besoin de l'onglet inspiration

**Paramètres requis** :
```python
params = {
    "departure_id": "CRL",      # Code IATA départ (ex: Bruxelles)
    "arrival_id": "BCN",        # Code IATA arrivée (ex: Barcelone)
    "outbound_date": "2025-12-01",  # Date aller
    "return_date": "2025-12-05",    # Date retour
    "adults": 2,                # Nombre de passagers
    "currency": "EUR",          # Devise
    "language": "fr"            # Langue
}
```

**Utilisation dans l'inspiration** :
```python
def _search_flights_google_flights2(self, origin, destination, departure_date, return_date, adults):
    """
    Recherche de vols via Google Flights RapidAPI (nouvelle API)
    """
    url = "https://google-flights2.p.rapidapi.com/api/v1/searchFlights"
    
    headers = {
        "x-rapidapi-key": "bfded6814amshf70237b7208f148p143ee9jsn90a9ad24f875",
        "x-rapidapi-host": "google-flights2.p.rapidapi.com"
    }
    
    params = {
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": departure_date,
        "return_date": return_date,
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
        for flight in data.get('data', {}).get('flights', [])[:5]:
            flights.append({
                'airline': flight.get('airline', {}).get('name'),
                'price': flight.get('price', {}).get('raw'),
                'departure_time': flight.get('departure_time'),
                'arrival_time': flight.get('arrival_time'),
                'duration': flight.get('duration'),
                'stops': len(flight.get('layovers', [])),
                'booking_url': flight.get('booking_url')
            })
        
        return flights
        
    except Exception as e:
        logger.error(f"Erreur API Google Flights 2: {e}")
        return []
```

---

### 2. **Search Airport** (GET) - UTILE ⭐⭐

**Endpoint** : Visible dans la capture (Search Airport)

**Pourquoi ?**
- Convertir nom de ville en code IATA (Rome → FCO)
- Valider les codes d'aéroport
- Trouver l'aéroport le plus proche d'une ville

**Utilisation** :
```python
def _get_airport_code_api(self, city_name: str) -> str:
    """
    Trouve le code IATA d'une ville via API Google Flights
    """
    url = "https://google-flights2.p.rapidapi.com/api/v1/searchAirport"
    
    params = {
        "query": city_name,
        "language": "fr"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        # Retourner le premier résultat (aéroport principal)
        if data.get('data', {}).get('airports'):
            return data['data']['airports'][0]['code']
        
        # Fallback sur dictionnaire statique
        return self._get_airport_code_static(city_name)
        
    except Exception as e:
        # Fallback sur dictionnaire statique
        return self._get_airport_code_static(city_name)
```

---

### 3. **Get Calendar Picker** (GET) - OPTIONNEL ⭐

**Endpoint** : Visible dans la capture (Get Calendar Picker)

**Pourquoi ?**
- Trouver les dates les moins chères sur un mois
- Proposer des alternatives si le budget est dépassé
- Fonctionnalité "Dates flexibles"

**Utilisation future** :
```python
# Si le budget est dépassé, proposer des dates alternatives
if total_price > budget:
    cheaper_dates = self._get_cheaper_dates_calendar(origin, destination, month)
```

---

## 🚫 Endpoints NON NÉCESSAIRES pour l'Inspiration

### ❌ Search Multi City Flights (POST)
- Pour voyages multi-destinations
- L'inspiration fait des voyages simples A→B

### ❌ Get Booking Details / Get Booking URL
- Pour finaliser une réservation
- L'inspiration génère juste des propositions, pas de réservation

### ❌ Get Price Graph / Get Calendar Grid
- Visualisations avancées
- Peut être ajouté plus tard pour enrichissement

---

## 🔧 Intégration dans le Système Cascade

### Position Recommandée

Ajouter Google Flights 2 comme **API prioritaire** dans la cascade :

```python
def _search_flights_cascade(self, origin, destination, departure_date, return_date, adults):
    """
    Système cascade avec Google Flights 2 en priorité
    """
    providers = [
        ("Google Flights 2", self._search_flights_google_flights2),  # ← NOUVEAU
        ("Skyscanner", self._search_flights_skyscanner),
        ("Booking.com", self._search_flights_booking),
        ("FlightSearch", self._search_flights_flightsearch)
    ]
    
    errors = []
    
    for provider_name, provider_func in providers:
        try:
            flights = provider_func(origin, destination, departure_date, return_date, adults)
            if flights:
                logger.info(f"✅ Vols trouvés via {provider_name}")
                return flights
            else:
                errors.append(f"{provider_name}: Aucun résultat")
        except Exception as e:
            errors.append(f"{provider_name}: {str(e)}")
            logger.warning(f"⚠️ {provider_name}: {str(e)}")
    
    # Si toutes échouent
    raise Exception(f"Impossible de trouver des vols. Erreurs: {', '.join(errors)}")
```

---

## 📋 Checklist d'Implémentation

### Configuration
- [ ] Vérifier que la clé RapidAPI fonctionne avec `google-flights2.p.rapidapi.com`
- [ ] Tester l'endpoint `/api/v1/searchFlights` manuellement
- [ ] Vérifier les limites du plan gratuit (requêtes/mois)

### Code
- [ ] Créer méthode `_search_flights_google_flights2()` dans `travel_inspector.py`
- [ ] Ajouter Google Flights 2 en priorité 1 dans la cascade
- [ ] Créer méthode `_get_airport_code_api()` (optionnel)
- [ ] Tester avec différentes destinations

### Tests
- [ ] Test BRU → BCN (court courrier)
- [ ] Test BRU → NYC (long courrier)
- [ ] Test avec dates flexibles
- [ ] Vérifier parsing des résultats
- [ ] Tester gestion des erreurs

---

## 🧪 Test Rapide

Pour vérifier si l'API fonctionne :

```bash
curl -X GET "https://google-flights2.p.rapidapi.com/api/v1/searchFlights?departure_id=BRU&arrival_id=BCN&outbound_date=2025-03-01&return_date=2025-03-05&adults=2&currency=EUR" \
  -H "x-rapidapi-key: bfded6814amshf70237b7208f148p143ee9jsn90a9ad24f875" \
  -H "x-rapidapi-host: google-flights2.p.rapidapi.com"
```

**Résultat attendu** :
```json
{
  "status": "success",
  "data": {
    "flights": [
      {
        "airline": {"name": "Ryanair"},
        "price": {"raw": 89.99, "currency": "EUR"},
        "departure_time": "2025-03-01T06:00:00",
        "arrival_time": "2025-03-01T08:30:00",
        "duration": "2h 30m",
        "layovers": []
      }
    ]
  }
}
```

---

## 🎯 Résumé

### Endpoints Prioritaires

1. **Search Flights** (GET) - ⭐⭐⭐ ESSENTIEL
   - Recherche de vols aller-retour
   - Base de l'onglet inspiration

2. **Search Airport** (GET) - ⭐⭐ UTILE
   - Conversion ville → code IATA
   - Améliore l'UX

3. **Get Calendar Picker** (GET) - ⭐ BONUS
   - Dates flexibles
   - Optimisation budget

### Action Immédiate

1. Tester l'endpoint `searchFlights` avec curl
2. Si ça fonctionne → Implémenter dans `travel_inspector.py`
3. Ajouter dans la cascade en priorité 1
4. Tester avec l'onglet inspiration

### Avantages de Google Flights 2

- ✅ Données Google (très fiables)
- ✅ Vous avez déjà la clé RapidAPI
- ✅ Bonne couverture internationale
- ✅ Prix compétitifs

---

**Note** : Cette API `google-flights2.p.rapidapi.com` est différente de l'ancienne `google-flights4.p.rapidapi.com` qui donnait l'erreur 403. Elle devrait fonctionner correctement.
