# 🚌 Implémentation complète du système Excursions d'un jour

## 📊 État d'avancement (Dernière mise à jour : 30/10/2025 10:27)

### ✅ Complété

#### 1. Interface de création manuelle (`templates/agency/generate_manual.html`)
- ✅ **Gestion des enfants** : Bouton "Ajouter des enfants" avec toggle fonctionnel
- ✅ **Autocomplétion Google Places** :
  - Hôtels avec extraction automatique de la ville
  - Aéroports (type `airport`)
  - Gares (sans restriction de type car `train_station` problématique)
  - Destinations (villes et attractions)
  - Adresses (avec restriction Belgique pour départs autocar)
- ✅ **Bouton Instagram** : Ajout du profil Instagram de l'hôtel (optionnel)
- ✅ **Configuration clé API Google** :
  - Clé `AIzaSyB8Nvg-pKx2zaEdduDqn8Exmm1nZhrGWFY` configurée dans `.env`
  - Accès dans le template via `g.agency_config` ou fallback sur config globale
- ✅ **Correction bugs** :
  - Validation regex dans `schemas.py` corrigée
  - Script Google Maps chargé avec callback `initializeApp()`

#### 2. Points techniques résolus
- ✅ Autocomplétion native Google Places (pas d'API proxy)
- ✅ Gestion des erreurs de clé API
- ✅ Listeners JavaScript pour tous les toggles
- ✅ Intégration avec le système existant

### 🔄 En cours / À faire

Les sections ci-dessous décrivent les tâches restantes pour l'implémentation complète du système d'excursions.

---

## 📋 Contexte

Le système actuel de génération de voyages est conçu pour des **séjours** (plusieurs jours avec hôtel). 
Il faut créer un flux complet et dédié pour les **excursions d'un jour** (autocar).

---

## 🎯 Objectifs

### 1. Template HTML dédié pour les fiches d'excursions
### 2. Page d'encodage adaptée aux excursions
### 3. API et services adaptés

---

## 📁 Fichiers à modifier

1. `services/template_engine.py` - Créer fonction dédiée pour excursions
2. `templates/agency/generate_manual.html` - Adapter l'interface d'encodage
3. `services/api_gatherer.py` - Gérer les destinations de type "attraction"
4. `services/ai_assistant.py` - Déjà fait ✅ (fonction `parse_day_trip_description`)

---

## 🔧 TÂCHE 1 : Template HTML pour excursions

### Fichier : `services/template_engine.py`

**Créer une nouvelle fonction `generate_day_trip_page_html()`**

#### Différences avec le template séjour :

| Élément | Séjour | Excursion |
|---------|--------|-----------|
| **En-tête** | Photo d'hôtel + étoiles + note Google | Photo de ville/attraction + date unique + prix/personne (pas de note Google) |
| **Dates** | Du X au Y | Date : X ou "Sur demande" |
| **Section "Inclus"** | Hôtel, vols, pension, transferts | Remplacé par "Programme de la journée" (Gemini reformule) |
| **Galerie photos** | 6+ photos d'hôtel | 6 photos de ville/attraction |
| **Comparateur prix** | Oui | Non (supprimé) |
| **Avis clients** | Oui | Non (supprimé) |
| **Section découverte** | Attractions multiples | 1 activité mise en avant avec photo + texte Gemini |
| **Restaurants** | Top 3 | Non (supprimé) |

#### Structure HTML recommandée

```html
<div class="story-card">
    <!-- Photo principale de la ville/attraction -->
    <img src="..." alt="...">
    
    <!-- Titre : nom de la destination -->
    <h2>Excursion à {destination}</h2>
    <p>📍 {ville}</p>
    
    <!-- Date unique ou "Sur demande" -->
    <p class="mt-4">📅 {date ou "Dates flexibles"}</p>
    
    <!-- Prix -->
    <div class="text-4xl font-bold mt-2">{prix}€</div>
    <p>par personne</p>
    
    <!-- Horaires -->
    <p class="text-sm">🕐 Départ {heure_depart} - Retour {heure_retour}</p>
    <p class="text-sm">📍 Départ depuis {adresse_depart}</p>
</div>

<!-- Programme de la journée (remplace "Inclus dans votre séjour") -->
<div class="instagram-card p-6">
    <h3 class="section-title">Programme de la journée</h3>
    <div class="space-y-4">
        <!-- Texte reformulé par Gemini depuis la description -->
        {programme_formate_gemini}
    </div>
</div>

<!-- Prix -->
<div class="instagram-card p-6">
    <h3 class="section-title">Tarif</h3>
    <div class="p-4 rounded-lg bg-green-600 text-white">
        <div class="text-center text-2xl font-bold">{prix}€ par personne</div>
        <p class="text-sm text-center mt-2">Transport en autocar inclus</p>
    </div>
</div>

<!-- Galerie (6 photos max) -->
<div class="instagram-card p-6">
    <h3 class="section-title">Photos</h3>
    <div class="image-grid">
        <!-- 6 photos de la destination -->
    </div>
</div>

<!-- 1 activité mise en avant -->
<div class="instagram-card p-6">
    <h3 class="section-title">À découvrir</h3>
    <img src="{activite_photo}" alt="..." class="w-full rounded-lg mb-4">
    <h4 class="font-bold">{activite_nom}</h4>
    <p>{activite_description_gemini}</p>
</div>

<!-- Footer identique au séjour -->
```

#### Données nécessaires pour le template

```python
{
    'destination': 'Rome',  # Ville ou attraction
    'date': '15 juin 2025' ou None,  # Date unique
    'price': 120,
    'departure_time': '08:00',
    'return_time': '20:00',
    'departure_address': 'Place de la Gare, Bruxelles',
    'program_formatted': 'Texte HTML formaté par Gemini',  # À récupérer depuis l'encodage
    'photos': ['url1', 'url2', ...],  # 6 photos de la destination
    'featured_activity': {
        'name': 'Colisée',
        'photo': 'url',
        'description': 'Texte Gemini attractif'  # À générer
    }
}
```

#### Appel Gemini pour le programme

Dans `api_gatherer.py` ou `template_engine.py`, ajouter :

```python
from services.ai_assistant import AIAssistant

def format_day_trip_program(raw_description: str, gemini_key: str) -> str:
    """Reformule la description brute en programme HTML attractif"""
    ai = AIAssistant(gemini_key)
    
    prompt = f"""
Transforme cette description d'excursion en un programme HTML attractif avec emojis.
Crée une liste chronologique claire et engageante.

Description brute :
{raw_description}

Format attendu :
<div class="flex items-start mb-3">
    <div class="text-2xl mr-3">🕐</div>
    <div>
        <h5 class="font-semibold">08:00 - Départ</h5>
        <p class="text-sm text-gray-600">Départ en autocar confortable depuis Bruxelles</p>
    </div>
</div>
[Répéter pour chaque étape]

Réponds UNIQUEMENT avec le HTML, sans markdown.
"""
    
    response = ai.model.generate_content(prompt)
    return response.text.strip()
```

---

## 🔧 TÂCHE 2 : Page d'encodage adaptée

### Fichier : `templates/agency/generate_manual.html`

#### Modifications à apporter :

**1. Détecter si c'est une excursion**

Ajouter au début du `<script>` :

```javascript
const isDayTrip = {{ 'true' if trip and trip.is_day_trip else 'false' }};

// Adapter l'interface selon le type
if (isDayTrip) {
    adaptInterfaceForDayTrip();
}

function adaptInterfaceForDayTrip() {
    // Masquer les sections non pertinentes
    document.querySelector('#hotel-section')?.classList.add('hidden');
    document.querySelector('#flight-section')?.classList.add('hidden');
    document.querySelector('#options-section')?.classList.add('hidden');
    
    // Afficher les champs spécifiques excursions
    document.querySelector('#day-trip-section')?.classList.remove('hidden');
}
```

**2. Ajouter une section HTML dédiée aux excursions**

Après les champs de base (destination, dates, prix), ajouter :

```html
<!-- Section excursion (masquée par défaut) -->
<div id="day-trip-section" class="hidden">
    <div class="form-section">
        <h3>📝 Programme de la journée</h3>
        
        <!-- Description détaillée -->
        <div class="mb-4">
            <label class="block mb-2">Description détaillée de la journée</label>
            <textarea 
                id="day_trip_description" 
                rows="8" 
                class="w-full p-3 border rounded"
                placeholder="Décrivez le déroulement complet : départ, pauses, visites, repas, retour...

Exemple :
Départ à 8h de la Place de la Gare à Bruxelles. Voyage confortable en autocar avec pause café à mi-parcours. Arrivée à Rome vers 12h30. Visite guidée du Colisée avec guide professionnel (durée 2h). Temps libre pour déjeuner dans le quartier de Trastevere. L'après-midi, visite du Vatican et de la Chapelle Sixtine. Temps libre pour shopping ou balade. Départ retour à 18h. Arrivée prévue à Bruxelles vers 23h."
            ></textarea>
        </div>
        
        <!-- Point de départ -->
        <div class="mb-4">
            <label class="block mb-2">Point de départ autocar</label>
            <input 
                type="text" 
                id="bus_departure_address" 
                class="w-full p-3 border rounded"
                placeholder="Ex: Place de la Gare, 1000 Bruxelles"
            >
            <small class="text-gray-600">L'autocomplétion d'adresses s'activera en tapant</small>
        </div>
        
        <!-- Horaires -->
        <div class="grid grid-cols-2 gap-4 mb-4">
            <div>
                <label class="block mb-2">Heure de départ</label>
                <input type="time" id="departure_time" class="w-full p-3 border rounded" value="08:00">
            </div>
            <div>
                <label class="block mb-2">Heure de retour</label>
                <input type="time" id="return_time" class="w-full p-3 border rounded" value="20:00">
            </div>
        </div>
    </div>
</div>
```

**3. Modifier l'autocomplétion destination**

Dans le JavaScript, changer la configuration de l'autocomplétion pour accepter villes ET attractions :

```javascript
// AVANT (actuel) :
const destinationAutocomplete = new google.maps.places.Autocomplete(
    destinationInput,
    { types: ['airport', '(cities)'] }  // Limité aux aéroports et villes
);

// APRÈS (pour excursions) :
if (isDayTrip) {
    // Pour les excursions : villes, attractions touristiques, monuments
    const destinationAutocomplete = new google.maps.places.Autocomplete(
        destinationInput,
        { 
            types: ['tourist_attraction', 'point_of_interest', '(cities)']
        }
    );
} else {
    // Pour les séjours : aéroports et villes
    const destinationAutocomplete = new google.maps.places.Autocomplete(
        destinationInput,
        { types: ['airport', '(cities)'] }
    );
}
```

**4. Ajouter l'autocomplétion d'adresses pour le départ autocar**

```javascript
if (isDayTrip) {
    const departureInput = document.getElementById('bus_departure_address');
    if (departureInput) {
        const departureAutocomplete = new google.maps.places.Autocomplete(
            departureInput,
            { 
                types: ['address'],
                componentRestrictions: { country: 'be' }  // Limiter à la Belgique
            }
        );
        
        departureAutocomplete.addListener('place_changed', function() {
            const place = departureAutocomplete.getPlace();
            if (place.formatted_address) {
                departureInput.value = place.formatted_address;
            }
        });
    }
}
```

**5. Adapter la soumission du formulaire**

```javascript
function collectFormData() {
    const formData = {
        destination: document.getElementById('destination').value,
        price: document.getElementById('price').value,
        // ... autres champs communs
    };
    
    if (isDayTrip) {
        // Champs spécifiques excursions
        formData.is_day_trip = true;
        formData.day_trip_description = document.getElementById('day_trip_description').value;
        formData.bus_departure_address = document.getElementById('bus_departure_address').value;
        formData.departure_time = document.getElementById('departure_time').value;
        formData.return_time = document.getElementById('return_time').value;
    } else {
        // Champs spécifiques séjours
        formData.hotel_name = document.getElementById('hotel_name').value;
        // ... etc
    }
    
    return formData;
}
```

---

## 🔧 TÂCHE 3 : Adapter l'API gatherer

### Fichier : `services/api_gatherer.py`

#### Modifications nécessaires :

**1. Détecter le type de destination**

```python
def gather_trip_data(form_data: dict, agency_config: dict) -> dict:
    """Enrichit les données du voyage avec les APIs externes"""
    
    is_day_trip = form_data.get('is_day_trip', False)
    
    if is_day_trip:
        return gather_day_trip_data(form_data, agency_config)
    else:
        return gather_regular_trip_data(form_data, agency_config)
```

**2. Créer `gather_day_trip_data()`**

```python
def gather_day_trip_data(form_data: dict, agency_config: dict) -> dict:
    """Enrichit les données pour une excursion d'un jour"""
    
    destination = form_data.get('destination', '')
    google_api_key = agency_config.get('google_api_key')
    gemini_api_key = agency_config.get('google_api_key')  # Même clé
    
    result = {
        'form_data': form_data,
        'api_data': {},
        'savings': 0,
        'comparison_total': 0
    }
    
    if not google_api_key:
        return result
    
    try:
        # 1. Rechercher le lieu (ville ou attraction)
        place_data = search_place(destination, google_api_key)
        
        if place_data:
            place_id = place_data.get('place_id')
            
            # 2. Photos de la destination (max 6)
            photos = get_place_photos(place_id, google_api_key, max_photos=6)
            result['api_data']['photos'] = photos
            
            # 3. Attractions proches (pour la section "À découvrir")
            nearby = get_nearby_attractions(place_id, google_api_key, max_results=3)
            result['api_data']['nearby_attractions'] = nearby
            
            # 4. Reformater le programme avec Gemini
            if form_data.get('day_trip_description'):
                from services.ai_assistant import AIAssistant
                ai = AIAssistant(gemini_api_key)
                
                # Reformater le programme
                program_html = format_day_trip_program(
                    form_data['day_trip_description'], 
                    gemini_api_key
                )
                result['api_data']['program_formatted'] = program_html
                
                # Générer description pour l'activité mise en avant
                if nearby and len(nearby) > 0:
                    featured = nearby[0]
                    activity_desc = generate_activity_description(
                        featured['name'], 
                        destination,
                        gemini_api_key
                    )
                    result['api_data']['featured_activity'] = {
                        'name': featured['name'],
                        'photo': featured.get('photo'),
                        'description': activity_desc
                    }
    
    except Exception as e:
        print(f"Erreur enrichissement excursion: {e}")
    
    return result


def generate_activity_description(activity_name: str, city: str, gemini_key: str) -> str:
    """Génère une description attractive d'une activité avec Gemini"""
    from services.ai_assistant import AIAssistant
    
    ai = AIAssistant(gemini_key)
    
    prompt = f"""
Écris un court paragraphe attractif (max 100 mots) sur "{activity_name}" à {city}.
Style marketing enthousiaste avec 1-2 emojis.
Focus sur l'expérience unique et les émotions.

Réponds directement avec le texte, sans titre.
"""
    
    response = ai.model.generate_content(prompt)
    return response.text.strip()
```

---

## 📝 Ordre d'implémentation recommandé

1. ✅ **D'abord** : Tester que la correction de date fonctionne
2. **Ensuite** : Implémenter le template HTML dédié (`template_engine.py`)
3. **Puis** : Adapter la page d'encodage (`generate_manual.html`)
4. **Enfin** : Adapter l'API gatherer (`api_gatherer.py`)

---

## 🧪 Tests à effectuer

### Test 1 : Création d'une excursion
1. Aller sur `/agency/generate/manual`
2. Cocher "Excursion d'un jour"
3. Remplir les champs spécifiques
4. Vérifier que les sections non pertinentes sont masquées
5. Soumettre le formulaire

### Test 2 : Génération de la fiche
1. Créer une excursion
2. Cliquer sur "Générer PDF"
3. Vérifier que le template excursion est utilisé
4. Vérifier la mise en page et le contenu

### Test 3 : Social media
1. Créer une excursion
2. Aller sur la page social media
3. Entrer une description
4. Générer le pack Instagram
5. Vérifier que l'IA analyse correctement

---

## 🚨 Points d'attention

1. **Ne pas oublier** de gérer le cas où `date_start` est vide pour les excursions
2. **Gemini API** : Vérifier que la clé est bien configurée
3. **Google Places** : Gérer les erreurs si l'API ne trouve pas la destination
4. **Photos** : Limiter à 6 max pour les excursions
5. **Prix** : Toujours afficher "par personne" pour les excursions

---

## 💾 Variables .env nécessaires

```bash
# Ces variables sont déjà configurées
GOOGLE_PLACES_API_KEY=...
GOOGLE_GEMINI_API_KEY=...  # Ou utiliser GOOGLE_PLACES_API_KEY

# Template Bannerbear pour excursions (à créer)
BANNERBEAR_DAY_TRIP_TEMPLATE_ID=VOTRE_UID_ICI
```

---

## ✅ Checklist finale

- [ ] Template HTML excursion créé
- [ ] Page d'encodage adaptée avec champs spécifiques
- [ ] Autocomplétion destination élargie (villes + attractions)
- [ ] Autocomplétion adresse départ autocar
- [ ] Section options masquée pour excursions
- [ ] API gatherer adapté
- [ ] Reformatage Gemini du programme fonctionnel
- [ ] Tests de bout en bout effectués
- [ ] Template Bannerbear excursion configuré (si social media)

---

**Bonne chance pour l'implémentation ! 🚀**
