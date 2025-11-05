# Endpoints Google Flights Requis pour l'Onglet Inspiration

Basé sur la capture d'écran de l'API Google Flights sur RapidAPI.

## 📋 API à utiliser

**Nom :** Google Flights 2  
**Host :** `google-flights2.p.rapidapi.com`

---

## ✅ Endpoints Nécessaires

### 1. **Search Flights** (Principal - REQUIS)
**Endpoint :** `/api/v1/searchFlights`  
**Méthode :** GET  
**Description :** Recherche de vols avec tous les détails

**Paramètres obligatoires :**
- `departure_id` (string) : Code IATA aéroport de départ (ex: "BRU", "CRL")
- `arrival_id` (string) : Code IATA aéroport d'arrivée (ex: "FCO", "MAD")
- `outbound_date` (string) : Date aller (YYYY-MM-DD)
- `return_date` (string) : Date retour (YYYY-MM-DD)
- `adults` (string) : Nombre d'adultes
- `travel_class` (string) : "ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"
- `currency` (string) : "EUR"

**Paramètres optionnels recommandés :**
- `show_hidden` (string) : "1" pour voir tous les vols
- `language_code` (string) : "fr-FR"
- `country_code` (string) : "BE"
- `search_type` (string) : "best" (meilleurs vols)

**Exemple de call actuel (qui ne fonctionne pas) :**
```python
url = "https://google-flights2.p.rapidapi.com/api/v1/searchFlights"
params = {
    "departure_id": "CRL",
    "arrival_id": "SVQ",
    "outbound_date": "2025-12-02",
    "return_date": "2025-12-06",
    "travel_class": "ECONOMY",
    "adults": "2",
    "show_hidden": "1",
    "currency": "EUR",
    "language_code": "fr-FR",
    "country_code": "BE",
    "search_type": "best"
}
```

**Problème détecté :**
- ✅ L'endpoint est correct
- ✅ Les paramètres sont corrects
- ❌ **L'API ne retourne AUCUN vol** → Problème de disponibilité ou route non supportée

---

## 🔍 Analyse du Problème

### Réponse actuelle de l'API
```json
{
    "status": false ou true,
    "message": "...",
    "data": null ou absent
}
```

### Solutions possibles

#### 1. **Utiliser `/api/v1/getFlightPrices` à la place**
Cet endpoint pourrait être plus fiable pour certaines routes.

**Endpoint :** `/api/v1/getFlightPrices`  
**Différence :** Retourne les prix des vols plutôt que les détails complets

#### 2. **Vérifier les codes aéroports**
- Certains aéroports régionaux (comme CRL - Charleroi) peuvent ne pas être supportés
- **Solution :** Essayer avec BRU (Bruxelles principal) à la place

#### 3. **Dates trop éloignées ou trop proches**
- Les APIs de vols ont souvent une fenêtre de disponibilité limitée
- **Solution :** Tester avec des dates dans 1-2 mois

#### 4. **Route non disponible**
- Certaines combinaisons d'aéroports ne retournent pas de résultats
- **Solution :** Implémenter un système de fallback vers d'autres aéroports

---

## 🛠️ Recommandations d'Implémentation

### Option A : Améliorer l'appel actuel

```python
def _search_flights_google_flights2(self, origin: str, destination: str, ...):
    """Version améliorée avec gestion d'erreurs"""
    
    url = "https://google-flights2.p.rapidapi.com/api/v1/searchFlights"
    
    params = {
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": departure_date,
        "return_date": return_date,
        "travel_class": "ECONOMY",
        "adults": str(adults),
        "show_hidden": "1",
        "currency": "EUR",
        "language_code": "fr-FR",
        "country_code": "BE",
        "search_type": "best"
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=20)
    data = response.json()
    
    # VÉRIFICATION ESSENTIELLE
    if not data.get('status'):
        logger.warning(f"API Google Flights status=false: {data.get('message')}")
        return []
    
    # Chercher les vols dans la structure correcte
    flights_data = data.get('data', {}).get('flights', [])
    
    if not flights_data:
        # Essayer d'autres structures possibles
        flights_data = data.get('flights', [])
    
    if not flights_data:
        logger.warning(f"Aucun vol retourné pour {origin} → {destination}")
        return []
    
    # Parser les vols...
```

### Option B : Mapper les aéroports problématiques

```python
# Dans TravelInspector
AIRPORT_FALLBACKS = {
    'CRL': 'BRU',  # Charleroi → Bruxelles
    'ORY': 'CDG',  # Orly → Charles de Gaulle
    'CIA': 'FCO',  # Ciampino → Fiumicino
}

def _get_best_airport(self, airport_code: str) -> str:
    """Retourne le meilleur aéroport pour les recherches API"""
    return self.AIRPORT_FALLBACKS.get(airport_code, airport_code)
```

### Option C : Système de retry avec variations

```python
def _search_flights_with_retry(self, origin, destination, ...):
    """Essaie plusieurs variantes si la première échoue"""
    
    # Tentative 1 : Codes originaux
    flights = self._search_flights_google_flights2(origin, destination, ...)
    if flights:
        return flights
    
    # Tentative 2 : Avec aéroports principaux
    main_origin = self.AIRPORT_FALLBACKS.get(origin, origin)
    main_dest = self.AIRPORT_FALLBACKS.get(destination, destination)
    
    if main_origin != origin or main_dest != destination:
        flights = self._search_flights_google_flights2(main_origin, main_dest, ...)
        if flights:
            return flights
    
    # Tentative 3 : Dates ±1 jour
    for date_offset in [-1, +1]:
        adjusted_dates = self._adjust_dates(departure_date, return_date, date_offset)
        flights = self._search_flights_google_flights2(
            origin, destination, *adjusted_dates, ...
        )
        if flights:
            return flights
    
    return []
```

---

## 📊 Tests à Effectuer

### 1. Tester avec des routes connues
```python
# Routes qui DOIVENT fonctionner
test_routes = [
    ("CDG", "FCO", "2025-03-15", "2025-03-20"),  # Paris → Rome
    ("BRU", "MAD", "2025-03-15", "2025-03-20"),  # Bruxelles → Madrid
    ("LHR", "BCN", "2025-03-15", "2025-03-20"),  # Londres → Barcelone
]
```

### 2. Vérifier la structure de réponse réelle
```python
# Ajouter des logs détaillés
print(f"Full response: {json.dumps(data, indent=2)}")
```

### 3. Contacter le support RapidAPI
Si l'API ne retourne vraiment aucun vol pour des routes valides, il peut y avoir :
- Un problème avec votre clé API
- Des restrictions sur votre plan d'abonnement
- Un bug de l'API elle-même

---

## ✅ Action Immédiate

**Pour déboguer maintenant :**

1. Testez avec BRU au lieu de CRL :
```python
"departure_id": "BRU"  # Au lieu de CRL
```

2. Testez avec des dates plus proches (dans 1 mois)

3. Ajoutez des logs pour voir la réponse COMPLÈTE :
```python
logger.info(f"Full API response: {json.dumps(data, indent=2)[:2000]}")
```

4. Vérifiez votre abonnement RapidAPI :
   - Êtes-vous sur le plan gratuit ou payant ?
   - Y a-t-il des restrictions de routes ?
   - Combien d'appels avez-vous faits aujourd'hui ?
