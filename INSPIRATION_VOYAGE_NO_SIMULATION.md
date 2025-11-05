# Système d'Inspiration de Voyages - Architecture Sans Simulation

## 🎯 Objectif

Le système d'inspiration de voyages a été **complètement refactorisé** pour éliminer toute simulation et codage en dur. Désormais :

- ✅ **Gemini AI** comprend et traduit les demandes utilisateurs
- ✅ **RapidAPI** fournit TOUTES les données (vols + hôtels)
- ✅ **Aucune donnée simulée** ni fallback
- ✅ **Gestion intelligente des erreurs** avec messages clairs

---

## 🏗️ Architecture

### 1. Analyse de la Demande (Gemini AI)

**Responsabilité** : Gemini AI doit extraire ET traduire toutes les informations nécessaires.

```python
# Gemini extrait :
{
    "destination": "Rome",
    "destination_airport_code": "FCO",  # ← Gemini DOIT fournir le code IATA
    "origin": "Bruxelles",
    "origin_airport_code": "BRU",        # ← Gemini DOIT fournir le code IATA
    "budget_pp": 400,
    "date_debut": "2025-10-03",
    "date_fin": "2025-10-09",
    "num_personnes": 2,
    "inclusions": ["petit-déjeuner"],
    "stars_min": 4
}
```

**Gestion des erreurs** :
- Si Gemini ne trouve pas le code aéroport → Exception avec message clair
- Si destination inconnue → Exception demandant de préciser
- Si budget manquant → Exception demandant le budget

### 2. Recherche de Données (RapidAPI)

#### A. Recherche de Vols (Google Flights API)

```python
def _search_flights_rapidapi(
    origin: str,          # Code IATA fourni par Gemini
    destination: str,     # Code IATA fourni par Gemini
    departure_date: str,
    return_date: str,
    adults: int
) -> List[Dict[str, Any]]:
    # Appel API Google Flights
    # Si erreur → Exception avec message clair
    # Si aucun vol → Exception demandant de changer dates/destination
```

**Gestion des erreurs** :
- Timeout → "La recherche a pris trop de temps. Veuillez réessayer."
- Aucun résultat → "Aucun vol trouvé pour [origine] → [destination]. Essayez d'autres dates."
- Erreur API → Message d'erreur technique clair

#### B. Recherche d'Hôtels (Booking.com API)

```python
def _search_hotels_rapidapi(
    destination: str,     # Nom de ville
    checkin: str,
    checkout: str,
    adults: int,
    max_price: int,       # Calculé : 70% du budget
    stars: int = None     # Optionnel
) -> List[Dict[str, Any]]:
    # Appel API Booking.com
    # Si erreur → Exception avec message clair
    # Si aucun hôtel → Exception demandant d'augmenter budget
```

**Gestion des erreurs** :
- Timeout → "La recherche d'hôtels a pris trop de temps."
- Aucun résultat → "Aucun hôtel dans votre budget. Veuillez augmenter le budget."
- Erreur API → Message d'erreur technique clair

### 3. Combinaison des Résultats

```python
def generate_travel_options(criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
    # 1. Chercher vols avec codes IATA de Gemini
    flights = self._search_flights_rapidapi(...)
    if not flights:
        raise Exception("Aucun vol trouvé...")
    
    # 2. Chercher hôtels
    hotels = self._search_hotels_rapidapi(...)
    if not hotels:
        raise Exception("Aucun hôtel trouvé...")
    
    # 3. Combiner intelligemment
    options = []
    for i, hotel in enumerate(hotels[:3]):
        flight = flights[min(i, len(flights)-1)]
        total_price = (hotel['price'] + flight['price']) // num_personnes
        
        if total_price <= budget * 1.1:  # Tolérance 10%
            options.append({...})
    
    if not options:
        raise Exception("Aucune combinaison dans votre budget...")
    
    return options
```

---

## 🚫 Ce Qui a Été Supprimé

### 1. Dictionnaire Codé en Dur

```python
# ❌ SUPPRIMÉ
AIRPORT_CODES = {
    'Rome': 'FCO',
    'Barcelone': 'BCN',
    # ... 70+ codes
}
```

**Raison** : Gemini AI doit connaître ces codes. Si Gemini ne les connaît pas, c'est un problème qu'il faut signaler à l'utilisateur.

### 2. Fonction de Fallback

```python
# ❌ SUPPRIMÉ
def _generate_fallback_option(self, criteria, index):
    # Génération de données simulées
    return {
        'hotel': {
            'name': f'Hotel {type} {destination}',  # Fake
            'price': int(budget * 0.65),            # Fake
        },
        'flight': {
            'airline': 'Brussels Airlines',         # Fake
            'price': int(budget * 0.35),            # Fake
        },
        'is_simulated': True
    }
```

**Raison** : Aucune donnée simulée n'est acceptable. Si les APIs ne trouvent rien, on renvoie une erreur claire.

### 3. Logique Hybride

```python
# ❌ SUPPRIMÉ
if self.use_real_apis:
    # Vraies données
else:
    # Fallback vers simulation
```

**Raison** : Toujours utiliser les vraies APIs. Si RapidAPI n'est pas disponible, erreur au démarrage.

---

## ✅ Nouvelle Logique de Validation

### Validation des Critères Gemini

```python
def _validate_criteria(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
    # Destination obligatoire
    if not criteria.get('destination'):
        raise ValueError("La destination n'a pas pu être identifiée. Veuillez préciser la ville.")
    
    # Code aéroport destination OBLIGATOIRE
    if not criteria.get('destination_airport_code'):
        raise ValueError(
            f"Le code aéroport pour {criteria.get('destination')} n'a pas pu être déterminé. "
            "Veuillez préciser une destination avec un aéroport international."
        )
    
    # Code aéroport origine OBLIGATOIRE
    if not criteria.get('origin_airport_code'):
        raise ValueError(
            f"Le code aéroport pour {criteria.get('origin', 'la ville de départ')} "
            "n'a pas pu être déterminé. Veuillez préciser une ville de départ avec un aéroport."
        )
    
    # Budget OBLIGATOIRE
    if not criteria.get('budget_pp'):
        raise ValueError("Le budget par personne n'a pas pu être identifié. Veuillez préciser un budget.")
    
    return criteria
```

### Validation des Résultats API

```python
# Vols
if not flights:
    raise Exception(
        f"Aucun vol trouvé pour {origin} → {destination} aux dates demandées. "
        "Veuillez essayer d'autres dates ou destinations."
    )

# Hôtels
if not hotels:
    raise Exception(
        f"Aucun hôtel trouvé à {destination} dans votre budget ({budget}€ par personne). "
        "Veuillez augmenter le budget ou essayer une autre destination."
    )

# Combinaisons
if not options:
    raise Exception(
        f"Aucune combinaison vol+hôtel ne correspond à votre budget de {budget}€ par personne. "
        "Veuillez augmenter le budget."
    )
```

---

## 🔧 Initialisation Stricte

```python
def __init__(self, gemini_api_key: str, rapidapi_key: str = None):
    if not rapidapi_key:
        raise ValueError("RapidAPI key est requise pour effectuer des recherches")
    
    genai.configure(api_key=gemini_api_key)
    self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
    self.rapidapi_key = rapidapi_key
```

**Plus de logique conditionnelle** : RapidAPI est OBLIGATOIRE.

---

## 📊 Flux de Traitement

```
┌─────────────────────┐
│  Demande Utilisateur│
│  "4 jours à Rome,   │
│   budget 400€"      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   GEMINI AI         │
│  - Extraction       │
│  - Traduction IATA  │◄─── Si échec → Exception claire
│  - Validation       │
└──────────┬──────────┘
           │
           ▼
    ┌─────────────┐
    │  Codes IATA │
    │  BRU → FCO  │
    └──────┬──────┘
           │
           ├──────────────────┬──────────────────┐
           ▼                  ▼                  ▼
    ┌─────────────┐    ┌─────────────┐   ┌─────────────┐
    │ Google      │    │ Booking.com │   │ Validation  │
    │ Flights API │    │ Hotels API  │   │ Budget      │
    └──────┬──────┘    └──────┬──────┘   └──────┬──────┘
           │                  │                  │
           │◄─ Si échec      │◄─ Si échec       │◄─ Si échec
           │   → Exception    │   → Exception    │   → Exception
           │                  │                  │
           └──────────────────┴──────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  Combinaisons     │
                    │  Vol + Hôtel      │
                    │  2-3 options      │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │   Résultats       │
                    │   Utilisateur     │
                    └───────────────────┘
```

---

## 🎯 Messages d'Erreur Utilisateur

### Erreurs Gemini

| Situation | Message |
|-----------|---------|
| Destination non identifiée | "La destination n'a pas pu être identifiée. Veuillez préciser la ville de destination." |
| Code aéroport inconnu | "Le code aéroport pour Rome n'a pas pu être déterminé. Veuillez préciser une destination avec un aéroport international." |
| Budget manquant | "Le budget par personne n'a pas pu être identifié. Veuillez préciser un budget." |

### Erreurs APIs

| Situation | Message |
|-----------|---------|
| Aucun vol | "Aucun vol trouvé pour Bruxelles → Rome aux dates demandées. Veuillez essayer d'autres dates ou destinations." |
| Aucun hôtel | "Aucun hôtel trouvé à Rome dans votre budget (400€ par personne). Veuillez augmenter le budget ou essayer une autre destination." |
| Budget insuffisant | "Aucune combinaison vol+hôtel ne correspond à votre budget de 400€ par personne. Veuillez augmenter le budget." |
| Timeout | "La recherche de vols a pris trop de temps. Veuillez réessayer." |

---

## 🧪 Tests

### Lancement des Tests

```bash
cd /Users/oldibox/Library/CloudStorage/OneDrive-Personnel/VP/Odyssee
python services/travel_inspector.py
```

### Prérequis

```bash
# Variables d'environnement requises
GOOGLE_GEMINI_API_KEY=AIzaSyB8Nvg-pKx2zaEdduDqn8Exmm1nZhrGWFY
RAPIDAPI_KEY=bfded6814amshf70237b7208f148p143ee9jsn90a9ad24f875
```

### Scénarios de Test

1. **Test nominal** : "4 jours à Rome, budget 400€"
2. **Test avec ville de départ** : "Week-end à Barcelone départ de Paris, 300€"
3. **Test destination inconnue** : "3 jours à Atlantis, 500€" → Devrait échouer proprement
4. **Test budget trop bas** : "5 jours à New York, 100€" → Devrait dire "budget insuffisant"

---

## 📝 Configuration App.py

```python
from services.travel_inspector import search_travel_inspiration

@app.route('/agency/inspiration', methods=['POST'])
def search_inspiration():
    query = request.form.get('query')
    
    # Appel avec VRAIES clés API
    result = search_travel_inspiration(
        query=query,
        gemini_api_key=app.config['GOOGLE_GEMINI_API_KEY'],
        rapidapi_key=app.config['RAPIDAPI_KEY']
    )
    
    if result.get('success'):
        return render_template('agency/inspiration.html', 
                             options=result['options'],
                             criteria=result['criteria'])
    else:
        # Afficher l'erreur claire à l'utilisateur
        return render_template('agency/inspiration.html', 
                             error=result['error'])
```

---

## 🎓 Résumé

### Avant ❌

- Dictionnaire codé en dur avec 70+ codes d'aéroports
- Fallback vers données simulées si APIs échouent
- Logique hybride compliquée (vraies données OU simulation)
- Utilisateur ne sait pas si les données sont réelles

### Maintenant ✅

- Gemini AI traduit TOUT (y compris codes IATA)
- 100% données réelles via RapidAPI
- Échecs gérés avec messages clairs
- Utilisateur sait toujours qu'il a des vraies données

### Philosophie

> **"Mieux vaut une erreur claire qu'une fausse information"**

Si Gemini ne comprend pas → on demande de préciser
Si les APIs ne trouvent rien → on explique pourquoi et comment ajuster
Si le budget est insuffisant → on le dit clairement

**AUCUNE SIMULATION. JAMAIS.**
