# 🌟 Système d'Inspiration de Voyages - Documentation

## Vue d'ensemble

Le système d'inspiration de voyages permet aux utilisateurs de décrire leur voyage idéal en langage naturel, et l'IA trouvera automatiquement les meilleures options de vols et d'hôtels correspondant à leurs critères.

## Architecture

### 1. Interface Utilisateur
- **Nouvel onglet "Inspiration"** dans la navigation principale
- **Page dédiée** : `/agency/inspiration`
- **Formulaire de recherche** : Champ de saisie pour décrire le voyage en langage naturel

### 2. Backend - Services

#### A. TravelInspector (`services/travel_inspector.py`)
Service principal qui gère toute la logique d'analyse et de génération d'options.

**Méthodes principales :**
- `analyze_travel_request()` : Analyse la demande en langage naturel avec Gemini AI
- `generate_travel_options()` : Génère 2-3 options de voyage basées sur les critères
- `search_and_aggregate()` : Méthode principale qui combine l'analyse et la génération

**Fonctionnalités :**
- ✅ Extraction intelligente des critères (destination, budget, dates, inclusions)
- ✅ Validation et nettoyage des données
- ✅ Génération de 3 options : Budget, Équilibré, Premium
- 🔄 Prêt pour intégration RapidAPI (actuellement en mode simulation)

#### B. Routes Flask (`app.py`)

**Routes ajoutées :**
```python
# Page d'inspiration
GET /agency/inspiration

# API de recherche
POST /api/inspire
```

**Protection et limites :**
- Authentification requise (`@agency_required`)
- Rate limiting : 30 requêtes/heure
- Logging des activités

### 3. Frontend

#### Template (`templates/agency/inspiration.html`)
- Interface moderne avec Tailwind CSS
- États de l'UI : Chargement, Erreur, Résultats, Aucun résultat
- Cards de résultats avec informations détaillées (hôtel + vol)

#### JavaScript
- Gestion des appels API avec `fetchWithCSRF`
- Affichage dynamique des résultats
- Bouton "Utiliser ce voyage" qui pré-remplit le formulaire de génération

## Flux utilisateur

```
1. Utilisateur clique sur "Inspiration" dans le menu
   ↓
2. Saisit sa demande en langage naturel
   Ex: "4 jours à Rome, hotel avec petit déjeuner, 
        départ entre le 03/10 et le 9/10 pour un 
        budget de 400€ par personne"
   ↓
3. Clic sur "Trouver des options de voyage"
   ↓
4. IA Gemini analyse la demande et extrait :
   - Destination : Rome
   - Budget : 400€/personne
   - Dates flexibles : 03/10 - 09/10
   - Inclusions : petit-déjeuner
   ↓
5. Système génère 2-3 options de voyage :
   - Option Budget (10% moins cher)
   - Option Équilibrée (au budget)
   - Option Premium (10% plus cher, si budget ≥ 350€)
   ↓
6. Affichage des résultats avec :
   - Nom et étoiles de l'hôtel
   - Détails du vol
   - Prix total
   - Bouton "Utiliser ce voyage"
   ↓
7. Clic sur "Utiliser ce voyage"
   ↓
8. Redirection vers /agency/generate avec 
   formulaire pré-rempli
   ↓
9. Génération du voyage comme d'habitude
```

## Exemples de requêtes

### 1. Requête simple
```
"Week-end à Barcelone, 300€ par personne, hôtel 4 étoiles"
```

**Extraction :**
```json
{
  "destination": "Barcelone",
  "budget_pp": 300,
  "num_personnes": 2,
  "stars_min": 4,
  "flexible_dates": false
}
```

### 2. Requête avec dates
```
"5 jours à Lisbonne du 15 au 20 mai, budget 500€, 2 personnes"
```

**Extraction :**
```json
{
  "destination": "Lisbonne",
  "date_debut": "2025-05-15",
  "date_fin": "2025-05-20",
  "budget_pp": 500,
  "num_personnes": 2
}
```

### 3. Requête avec inclusions
```
"Voyage romantique à Venise, all-inclusive, 600€ chacun"
```

**Extraction :**
```json
{
  "destination": "Venise",
  "budget_pp": 600,
  "inclusions": ["all-inclusive"],
  "num_personnes": 2
}
```

## Intégration RapidAPI (Future)

### APIs recommandées

#### 1. Vols - Skyscanner API
```python
# Endpoint : /api/v1/flights/search
params = {
    'origin': 'BRU',
    'destination': 'ROM',
    'departure_date': '2025-10-03',
    'return_date': '2025-10-09',
    'adults': 2,
    'max_price': 200  # Par personne
}
```

#### 2. Hôtels - Booking.com API
```python
# Endpoint : /api/v1/hotels/search
params = {
    'city': 'Rome',
    'checkin': '2025-10-03',
    'checkout': '2025-10-09',
    'adults': 2,
    'max_price': 400,
    'stars': [3, 4, 5],
    'meal_plan': 'breakfast'
}
```

### Modification du code pour RapidAPI

Dans `services/travel_inspector.py`, méthode `generate_travel_options()` :

```python
def generate_travel_options(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Génère 2-3 options de voyage basées sur les critères
    """
    
    # 1. Appeler l'API de vols
    flights = self._search_flights(
        origin='BRU',
        destination=self._get_airport_code(criteria['destination']),
        departure_date=criteria.get('date_debut'),
        return_date=criteria.get('date_fin'),
        adults=criteria.get('num_personnes', 2),
        max_price=criteria['budget_pp'] * 0.4  # 40% du budget
    )
    
    # 2. Appeler l'API d'hôtels
    hotels = self._search_hotels(
        city=criteria['destination'],
        checkin=criteria.get('date_debut'),
        checkout=criteria.get('date_fin'),
        adults=criteria.get('num_personnes', 2),
        max_price=criteria['budget_pp'] * 0.6,  # 60% du budget
        stars=criteria.get('stars_min'),
        meal_plan=criteria.get('inclusions')
    )
    
    # 3. Combiner les résultats
    options = []
    for hotel in hotels[:3]:
        for flight in flights:
            total = flight['price'] + hotel['price']
            if total <= criteria['budget_pp']:
                options.append({
                    'destination': criteria['destination'],
                    'total_price': total,
                    'hotel': hotel,
                    'flight': flight,
                    'date_debut': criteria.get('date_debut'),
                    'date_fin': criteria.get('date_fin'),
                    'inclusions': criteria.get('inclusions', [])
                })
    
    # 4. Trier par prix et retourner top 3
    return sorted(options, key=lambda x: x['total_price'])[:3]
```

## Configuration requise

### Variables d'environnement
```bash
# Clé Gemini AI (déjà configurée)
GOOGLE_GEMINI_API_KEY=votre_clé_ici

# Pour intégration RapidAPI future
RAPIDAPI_KEY=votre_clé_rapidapi
RAPIDAPI_FLIGHTS_HOST=skyscanner-api.rapidapi.com
RAPIDAPI_HOTELS_HOST=booking-com.rapidapi.com
```

### Permissions
- Accessible à tous les utilisateurs d'agence (admin et sellers)
- Rate limiting : 30 requêtes/heure par utilisateur

## État actuel

### ✅ Implémenté (MVP)
1. Interface utilisateur complète et moderne
2. Analyse intelligente des demandes en langage naturel
3. Extraction des critères (destination, budget, dates, inclusions)
4. Génération de 3 options simulées (Budget, Équilibré, Premium)
5. Affichage des résultats avec cards attractives
6. Bouton "Utiliser ce voyage" pour pré-remplir le formulaire
7. Logging des activités
8. Gestion des erreurs et cas limites

### 🔄 À faire (Phase 2)
1. Intégration RapidAPI pour vraies données de vols
2. Intégration RapidAPI pour vraies données d'hôtels
3. Système de cache pour optimiser les performances
4. Sauvegarde des recherches favorites
5. Comparaison d'options côte à côte
6. Export des résultats en PDF
7. Notifications quand les prix baissent

## Tests

### Test manuel

1. Démarrer l'application
2. Se connecter avec un compte agence
3. Cliquer sur "Inspiration" dans le menu
4. Saisir une demande, par exemple :
   ```
   "4 jours à Rome, hotel avec petit déjeuner, 
    départ entre le 03/10 et le 9/10 pour un 
    budget de 400€ par personne"
   ```
5. Vérifier l'affichage de 2-3 options
6. Cliquer sur "Utiliser ce voyage"
7. Vérifier le pré-remplissage du formulaire

### Test du service

```bash
# Dans le terminal
cd /path/to/odyssee
python services/travel_inspector.py
```

Cela lancera les tests intégrés qui vérifient :
- Le parsing de différents types de requêtes
- La génération d'options
- La validation des données

## Support et maintenance

### Logs
Les activités d'inspiration sont loguées avec :
```python
log_activity(
    action='inspiration_search',
    user_id=g.user.id,
    agency_id=g.agency.id,
    details=f"Recherche: {query[:100]}"
)
```

### Monitoring
- Vérifier les logs pour détecter les erreurs Gemini
- Surveiller le rate limiting (30 req/h)
- Analyser les requêtes utilisateurs pour améliorer l'IA

## Évolutions futures

### Phase 2 - Intégration APIs réelles
- [ ] Connexion RapidAPI
- [ ] API Skyscanner pour vols
- [ ] API Booking.com pour hôtels
- [ ] Gestion du cache

### Phase 3 - Fonctionnalités avancées
- [ ] Sauvegarde des recherches
- [ ] Alertes prix
- [ ] Comparaison avancée
- [ ] Export PDF

### Phase 4 - Optimisations
- [ ] ML pour affiner les recommandations
- [ ] Historique des recherches
- [ ] Suggestions personnalisées basées sur l'historique

## Dépannage

### Problème : "Service d'inspiration non configuré"
**Solution :** Vérifier que `GOOGLE_GEMINI_API_KEY` est bien définie dans `.env`

### Problème : Aucun résultat trouvé
**Causes possibles :**
1. Budget trop bas (< 200€)
2. Destination mal formatée
3. Erreur de l'API Gemini

**Solution :** Vérifier les logs pour plus de détails

### Problème : Rate limit atteint
**Solution :** Attendre 1 heure ou augmenter la limite dans le code

## Conclusion

Le système d'inspiration de voyages est maintenant opérationnel en mode MVP. Il offre une expérience utilisateur fluide et intuitive, avec une IA qui comprend les demandes en langage naturel et propose des options de voyage pertinentes.

La structure du code est prête pour l'intégration future des APIs réelles de vols et d'hôtels, ce qui transformera le système de simulation en véritable moteur de recherche de voyages.

---

**Auteur :** Cline AI  
**Date :** 11/01/2025  
**Version :** 1.0.0 (MVP)
