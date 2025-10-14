# 📋 CONTEXTE PROJET ODYSSÉE SAAS - Mise à jour du 14/10/2025

## 🎯 OBJECTIF DU PROJET
Plateforme SaaS multi-tenant permettant à plusieurs agences de voyages de :
- Générer des offres de voyages personnalisées avec **Assistant IA Conversationnel**
- Gérer leurs clients et vendeurs
- Publier automatiquement des fiches sur leurs sites web
- Encaisser via Stripe
- Avoir leur propre branding (logo, couleurs, templates)

## 🏗️ ARCHITECTURE TECHNIQUE

### Stack Technologique
- **Backend** : Flask (Python)
- **Base de données** : SQLite (dev) / PostgreSQL (prod Railway)
- **Frontend** : Tailwind CSS + JavaScript Vanilla
- **Sécurité** : Flask-Bcrypt + Cryptography (Fernet)
- **IA** : Google Gemini API (parsing prompts, génération contenu)
- **APIs Externes** : Google Places, YouTube Data API
- **Déploiement prévu** : Railway (multi-domaines)

### Structure des Fichiers
```
odyssee-saas/
├── app.py                    # Application Flask principale ✅ MISE À JOUR (14 Oct)
├── models.py                 # Modèles SQLAlchemy ✅ COMPLET
├── config.py                 # Configuration ✅ COMPLET
├── requirements.txt          # Dépendances Python ✅
├── requirements-light.txt    # Version Mac sans psycopg2 ✅
├── .env                      # Variables d'environnement (NON COMMITÉ)
├── .gitignore               # ✅ COMPLET
├── create_agency.py         # Script helper ✅
├── utils/
│   ├── __init__.py          # ✅
│   └── crypto.py            # Système de chiffrement ✅ COMPLET
├── services/                # ✅ Phase 4 - Backend Créé
│   ├── __init__.py          # ✅ À créer (vide)
│   ├── ai_assistant.py      # ✅ CRÉÉ (14 Oct) - 420 lignes
│   ├── api_gatherer.py      # 🚧 À développer (Phase 5)
│   ├── template_engine.py   # 🚧 À développer (Phase 5)
│   └── publication.py       # 🚧 À développer (Phase 6)
├── templates/
│   ├── base.html            # Template de base ✅
│   ├── login.html           # Page de connexion ✅
│   ├── home.html            # Page d'accueil ✅
│   ├── super_admin/
│   │   ├── dashboard.html   # Dashboard super-admin ✅
│   │   ├── agencies.html    # Gestion agences ✅ COMPLET
│   │   └── agency_users.html # Gestion utilisateurs ✅ COMPLET
│   └── agency/              # 🚧 Phase 4 - Frontend à créer
│       ├── dashboard.html   # 🚧 À créer (~200 lignes)
│       ├── generate.html    # 🚧 À créer (~500 lignes) - Wizard IA
│       ├── trips.html       # 🚧 À créer (~250 lignes)
│       └── clients.html     # 🚧 À créer (~200 lignes)
├── static/
│   ├── css/
│   │   └── wizard.css       # 🚧 À créer (~300 lignes)
│   └── js/
│       └── wizard.js        # 🚧 À créer (~800 lignes)
└── migrations/              # Alembic (auto-généré)
```

## 📊 MODÈLES DE DONNÉES

### Agency (Agence)
```python
- id (PK)
- name (str) : "Voyages Privilèges"
- subdomain (str, unique) : "voyages-privileges"
- logo_url (str, nullable)
- primary_color (str) : "#3B82F6"
- template_name (str) : "classic" | "modern" | "luxury"
- google_api_key_encrypted (text, nullable) 🔐
- stripe_api_key_encrypted (text, nullable) 🔐
- mail_config_encrypted (text, nullable) 🔐
- ftp_config_encrypted (text, nullable) 🔐
- contact_email, contact_phone, contact_address, website_url
- is_active (bool)
- subscription_tier : "basic" | "pro" | "enterprise"
- monthly_generation_limit (int)
- current_month_usage (int)
- usage_reset_date (date)
- created_at, updated_at
- Relations : users[], trips[], clients[]
```

### User (Utilisateur)
```python
- id (PK)
- agency_id (FK Agency, nullable pour super_admin)
- username (str, unique)
- password (str) : Hash bcrypt
- pseudo (str)
- email (str, unique)
- phone (str, nullable)
- role (str) : "super_admin" | "agency_admin" | "seller"
- margin_percentage (int) : 80 par défaut
- generation_count (int)
- last_generation_date (date)
- daily_generation_limit (int) : 5 par défaut
- is_active (bool)
- created_at, last_login
- Relations : trips[]
```

### Client
```python
- id (PK)
- agency_id (FK Agency)
- first_name, last_name
- email, phone, address
- created_at
- Relations : trips[]
```

### Trip (Voyage)
```python
- id (PK)
- agency_id (FK Agency)
- user_id (FK User)
- client_id (FK Client, nullable)
- full_data_json (text) : Toutes les données du voyage
- hotel_name, destination, price
- status : "proposed" | "assigned" | "sold"
- is_published (bool)
- published_filename (str, nullable)
- is_ultra_budget (bool)
- 🔥 NOUVEAU : is_day_trip (bool) : True si excursion d'un jour
- 🔥 NOUVEAU : transport_type (str) : "avion" | "train" | "autocar" | "voiture"
- 🔥 NOUVEAU : bus_departure_address (text, nullable) : Point de départ autocar
- 🔥 NOUVEAU : travel_duration_minutes (int, nullable) : Durée trajet en minutes
- 🔥 NOUVEAU : departure_time (time, nullable) : Heure départ (voyage 1 jour)
- 🔥 NOUVEAU : return_time (time, nullable) : Heure retour (voyage 1 jour)
- client_published_filename (str, nullable)
- stripe_payment_link (text, nullable)
- down_payment_amount (int, nullable)
- balance_due_date (date, nullable)
- document_filenames (text, nullable)
- created_at, assigned_at, sold_at
- Relations : invoices[]
```

### Invoice (Facture)
```python
- id (PK)
- invoice_number (str, unique)
- trip_id (FK Trip)
- created_at
```

## 🔐 SYSTÈME DE SÉCURITÉ

### Chiffrement (utils/crypto.py)
- **Clé maître** : MASTER_ENCRYPTION_KEY dans .env
- **Algorithme** : Fernet (chiffrement symétrique)
- **Usage** : Chiffre les clés API, configs mail/FTP des agences
- **⚠️ CRITIQUE** : Ne JAMAIS changer la clé maître en prod (données perdues)

### Authentification
- **Middleware** : `identify_agency()` (détecte l'agence par sous-domaine)
- **Décorateurs** :
  - `@login_required` : Vérifie connexion
  - `@super_admin_required` : Réservé super-admin
  - `@agency_admin_required` : Admin d'agence ou super-admin

### Rôles et Permissions
1. **super_admin** : Gère toute la plateforme, aucune agence
2. **agency_admin** : Gère son agence (utilisateurs, config)
3. **seller** : Crée des voyages, gère ses clients

## 🚀 PLANNING DE DÉVELOPPEMENT

### ✅ Phase 1 : Setup Initial (TERMINÉE)
- Structure de projet complète
- Configuration de base
- Base de données avec tous les modèles
- Système de chiffrement fonctionnel

### ✅ Phase 2 : Authentification Multi-Niveau (TERMINÉE)
- Login super-admin
- Login agence (admin + vendeurs)
- Middleware d'identification par sous-domaine
- Décorateurs de sécurité

### ✅ Phase 3 : Interface Super-Admin (TERMINÉE ✅)

#### ✅ Complété :
1. **Dashboard super-admin** (/super-admin)
   - Statistiques globales
   - État de la plateforme
   - Activité récente

2. **CRUD Agences complet** (/super-admin/agencies)
   - ✅ GET : Liste des agences
   - ✅ POST : Créer une agence
   - ✅ PUT : Modifier une agence
   - ✅ DELETE : Supprimer une agence (avec protection)
   - Modal création/édition
   - Modal confirmation suppression
   - Toggle actif/inactif
   - Chiffrement automatique des clés API

3. **Gestion des utilisateurs par agence** ✅
   - ✅ Page : `/super-admin/agencies/<id>/users`
   - ✅ API GET/POST : Liste et création d'utilisateurs
   - ✅ API PUT/DELETE : Modification et suppression
   - ✅ Créer des agency_admin pour une agence
   - ✅ Créer des sellers pour une agence
   - ✅ Modifier/désactiver des utilisateurs
   - ✅ Réinitialiser mot de passe
   - ✅ Protection super-admin (impossible à modifier/supprimer)
   - ✅ Suppression intelligente (désactive si voyages, sinon supprime)
   - ✅ Interface avec tableau et statistiques temps réel
   - ✅ Quotas configurables (limite quotidienne + marge)

### 🔥 Phase 4 : Interface Agence (EN COURS - PRIORITÉ ABSOLUE)

#### 🎯 Système de Génération de Voyage avec Assistant IA

##### **Architecture du Système**

Le système de génération utilise un **Wizard Conversationnel IA** qui guide l'utilisateur étape par étape :

```
┌─────────────────────────────────────────────────┐
│  ÉTAPE 0 : Prompt Initial (Mode IA)             │
│  "Voyage en autocar à Rome, Colisée + Vatican"  │
│                 ↓                               │
│  Parsing IA (Gemini) → Structure les données    │
│                 ↓                               │
│  WIZARD CONVERSATIONNEL (8-10 étapes)           │
│  Chaque question pré-remplie par l'IA           │
│  L'utilisateur valide ou modifie                │
│                 ↓                               │
│  GÉNÉRATION DE LA FICHE                         │
└─────────────────────────────────────────────────┘
```

##### **1. Page de Génération (`/agency/generate`)**

###### **Mode IA (Par défaut)**
```
┌─────────────────────────────────────────────────┐
│  🚀 Créer un Voyage                             │
├─────────────────────────────────────────────────┤
│  [🤖 Assistant IA] [📝 Manuel]                  │
│                                                 │
│  💬 Décrivez votre voyage en langage naturel    │
│  ┌───────────────────────────────────────────┐ │
│  │ "Voyage en autocar à Rome, excursion     │ │
│  │  Colisée + Vatican, 3 jours, 100€/pers"  │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  💡 Exemples :                                  │
│  • Week-end Paris, train, 4★, 350€             │
│  • Excursion Bruges, autocar, 1 jour, 50€      │
│                                                 │
│  [✨ Démarrer le Wizard]                        │
└─────────────────────────────────────────────────┘
```

###### **Wizard Conversationnel (Étapes Dynamiques)**

Le nombre d'étapes varie selon le type de voyage détecté par l'IA :

**VOYAGE AVEC HÉBERGEMENT (8-10 étapes)**
1. 🏨 Quel hôtel ? (pré-rempli si mentionné)
2. 📍 Destination (pré-rempli depuis le prompt)
3. 🎯 Lieux d'intérêt (liste pré-remplie + bouton ➕)
4. 🚌 Transport (avion/train/autocar/voiture)
   - Si autocar → 📍 Point de départ + ⏱️ Durée trajet
5. 🗓️ Dates du séjour (date picker)
6. ⭐ Catégorie de l'hôtel (2-5 étoiles)
7. 🍽️ Formule repas (logement seul → All-In)
8. 💰 Prix & Services
9. ✅ Récapitulatif

**VOYAGE D'UN JOUR / EXCURSION (6-8 étapes)**
1. 📍 Destination
2. 🎯 Lieux d'intérêt
3. 🚌 Transport (obligatoirement autocar)
   - 📍 Point de départ
   - ⏱️ Durée trajet
4. ⏰ Horaires (heure départ + heure retour)
5. 📋 Programme de la journée (timeline)
6. 💰 Prix & Inclus/Non inclus
7. ✅ Récapitulatif

###### **Fonctionnalités Clés du Wizard**

**Pré-remplissage Intelligent**
```javascript
// L'IA parse le prompt et extrait :
{
  "transport_type": "autocar",
  "destination": "Rome, Italie",
  "is_day_trip": false,
  "activities": ["Colisée", "Vatican"],
  "price": 100,
  "estimated_duration": 3
}

// Ces données pré-remplissent les champs
// L'utilisateur voit : "L'IA a détecté : Rome"
// Le champ est déjà rempli mais modifiable
```

**Gestion des Lieux d'Intérêt**
```html
┌─────────────────────────────────────────────────┐
│  🎯 Lieux d'intérêt                             │
│  L'IA a détecté ces activités :                 │
│                                                 │
│  ✅ [Colisée                    ] [✏️] [🗑️]    │
│  ✅ [Vatican                    ] [✏️] [🗑️]    │
│                                                 │
│  [➕ Ajouter un lieu d'intérêt]                │
└─────────────────────────────────────────────────┘
```

**Transport Autocar (Champs Spécifiques)**
```html
┌─────────────────────────────────────────────────┐
│  🚌 Transport                                   │
│  🔵 Autocar (sélectionné)                       │
│                                                 │
│  📍 Point de départ de l'autocar :              │
│  [Place de la Gare, Bruxelles            ]      │
│                                                 │
│  ⏱️ Durée estimée du trajet :                  │
│  [15] heures [30] minutes                       │
└─────────────────────────────────────────────────┘
```

**Voyage d'un Jour (Template Spécial)**
```html
┌─────────────────────────────────────────────────┐
│  📅 Type de séjour                              │
│                                                 │
│  ☑️ Voyage d'un jour (excursion sans nuitée)   │
│  ☐ Séjour avec hébergement                     │
│                                                 │
│  ⏰ Horaires :                                  │
│  Départ : [08:00]  Retour : [20:00]            │
│                                                 │
│  → Pas de questions sur l'hôtel/dates          │
│  → Focus sur le programme de la journée         │
└─────────────────────────────────────────────────┘
```

**Programme de la Journée (Voyage 1 jour)**
```html
┌─────────────────────────────────────────────────┐
│  📋 Programme de la journée                     │
│                                                 │
│  08:00 - Départ de [Point de départ]           │
│  10:00 - Pause café                             │
│  12:00 - Arrivée à Rome                         │
│  12:30 - Déjeuner libre                         │
│  14:00 - Visite guidée Colisée                  │
│  16:00 - Visite Vatican                         │
│  17:30 - Temps libre                            │
│  18:30 - Départ retour                          │
│  20:00 - Arrivée [Point de départ]              │
│                                                 │
│  [✏️ Personnaliser le programme]                │
└─────────────────────────────────────────────────┘
```

##### **2. Mode Manuel (Formulaire Complet)**

Pour les professionnels qui veulent tout remplir d'un coup :

```html
┌─────────────────────────────────────────────────┐
│  📝 Création Manuelle de Voyage                 │
├─────────────────────────────────────────────────┤
│  [🤖 ← Retour Mode IA]                         │
│                                                 │
│  🏨 Détails du Séjour                          │
│  [Nom hôtel] [Destination] [Dates]             │
│                                                 │
│  ✈️ Transport                                   │
│  • Avion                                        │
│  • Train                                        │
│  • 🚌 Autocar                                   │
│    └─ [Point de départ]                        │
│    └─ [Durée trajet]                           │
│  • Voiture                                      │
│                                                 │
│  📅 Type de voyage                              │
│  ☐ Voyage d'un jour                            │
│    └─ [Heure départ] [Heure retour]           │
│  ☑️ Séjour avec hébergement                     │
│                                                 │
│  (... suite du formulaire complet)              │
└─────────────────────────────────────────────────┘
```

##### **3. Backend - Routes & APIs**

###### **Routes Flask à Créer**

```python
# Dans app.py

# === ROUTES PAGES ===

@app.route('/agency/dashboard')
@login_required
@agency_required  # Nouveau décorateur (agency_admin ou seller)
def agency_dashboard():
    """Dashboard de l'agence"""
    pass

@app.route('/agency/generate')
@login_required
@agency_required
def generate_trip():
    """Page de génération de voyage"""
    # Passer la clé Google API de l'agence au template
    google_api_key = g.agency_config['google_api_key']
    return render_template('agency/generate.html', 
                         google_api_key=google_api_key,
                         user_margin=g.user.margin_percentage)

@app.route('/agency/trips')
@login_required
@agency_required
def trips_list():
    """Liste des voyages de l'agence"""
    pass

@app.route('/agency/clients')
@login_required
@agency_required
def clients_list():
    """Gestion des clients"""
    pass

# === API GÉNÉRATION ===

@app.route('/api/ai-parse-prompt', methods=['POST'])
@login_required
@agency_required
def ai_parse_prompt():
    """
    Parse un prompt en langage naturel avec Gemini
    
    Input: { "prompt": "Voyage en autocar à Rome..." }
    Output: {
        "transport_type": "autocar",
        "destination": "Rome, Italie",
        "is_day_trip": false,
        "activities": ["Colisée", "Vatican"],
        "price": 100,
        "hotel_name": null,
        "estimated_duration": 3
    }
    """
    from services.ai_assistant import parse_travel_prompt
    
    prompt = request.json.get('prompt')
    parsed_data = parse_travel_prompt(prompt)
    
    return jsonify(parsed_data)

@app.route('/api/generate-preview', methods=['POST'])
@login_required
@agency_required
def generate_preview():
    """
    Génère la fiche de voyage avec appels API externes
    
    Input: { wizard_data complètes }
    Output: {
        "success": true,
        "api_data": {
            "photos": [...],
            "videos": [...],
            "reviews": {...},
            "attractions": {...}
        },
        "form_data": {...},
        "margin": 123,
        "savings": 456
    }
    """
    from services.api_gatherer import gather_trip_data
    
    data = request.json
    
    # Vérifier le quota de génération
    if not check_generation_quota(g.user, g.agency):
        return jsonify({
            'success': False,
            'error': 'Quota de génération dépassé'
        }), 429
    
    # Appeler les APIs externes
    enriched_data = gather_trip_data(data, g.agency_config)
    
    # Incrémenter les compteurs
    increment_generation_counters(g.user, g.agency)
    
    return jsonify(enriched_data)

@app.route('/api/render-html-preview', methods=['POST'])
@login_required
@agency_required
def render_html_preview():
    """
    Génère le HTML final de la fiche
    
    Input: { generatedData }
    Output: HTML complet (string)
    """
    from services.template_engine import render_trip_template
    
    data = request.json
    
    # Choisir le template selon le type de voyage
    template_type = 'day_trip' if data.get('is_day_trip') else 'standard'
    
    html = render_trip_template(
        data, 
        template_type,
        g.agency.template_name  # classic/modern/luxury
    )
    
    return html

@app.route('/api/trips', methods=['GET', 'POST'])
@login_required
@agency_required
def api_trips():
    """CRUD des voyages"""
    if request.method == 'GET':
        # Liste des voyages
        trips = Trip.query.filter_by(agency_id=g.agency.id).all()
        return jsonify([trip.to_dict() for trip in trips])
    
    elif request.method == 'POST':
        # Sauvegarder un nouveau voyage
        data = request.json
        
        # Créer le client si besoin
        client_id = None
        if data.get('status') == 'assigned':
            if data.get('client_id'):
                client_id = data['client_id']
            else:
                # Créer nouveau client
                new_client = Client(
                    agency_id=g.agency.id,
                    first_name=data['client_first_name'],
                    last_name=data['client_last_name'],
                    email=data['client_email'],
                    phone=data.get('client_phone')
                )
                db.session.add(new_client)
                db.session.flush()
                client_id = new_client.id
        
        # Créer le voyage
        new_trip = Trip(
            agency_id=g.agency.id,
            user_id=g.user.id,
            client_id=client_id,
            full_data_json=json.dumps(data),
            hotel_name=data['form_data']['hotel_name'],
            destination=data['form_data']['destination'],
            price=data['form_data']['pack_price'],
            status=data['status'],
            is_day_trip=data['form_data'].get('is_day_trip', False),
            transport_type=data['form_data'].get('transport_type'),
            bus_departure_address=data['form_data'].get('bus_departure_address'),
            travel_duration_minutes=calculate_duration_minutes(data),
            departure_time=data['form_data'].get('departure_time'),
            return_time=data['form_data'].get('return_time')
        )
        
        db.session.add(new_trip)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'trip': new_trip.to_dict()
        })

@app.route('/api/clients', methods=['GET', 'POST'])
@login_required
@agency_required
def api_clients():
    """CRUD des clients"""
    if request.method == 'GET':
        clients = Client.query.filter_by(agency_id=g.agency.id).all()
        return jsonify([client.to_dict() for client in clients])
    
    elif request.method == 'POST':
        # Créer un nouveau client
        data = request.json
        new_client = Client(
            agency_id=g.agency.id,
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data.get('phone'),
            address=data.get('address')
        )
        db.session.add(new_client)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'client': new_client.to_dict()
        })
```

##### **4. Services Backend**

###### **services/ai_assistant.py** (NOUVEAU)

```python
"""
Assistant IA pour le parsing de prompts et génération de contenu
Utilise Google Gemini API
"""

import google.generativeai as genai
import json
from typing import Dict, Any

def init_gemini(api_key: str):
    """Initialise Gemini avec la clé API de l'agence"""
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-pro')

def parse_travel_prompt(prompt: str, api_key: str) -> Dict[str, Any]:
    """
    Parse un prompt en langage naturel et extrait les informations
    
    Args:
        prompt: "Voyage en autocar à Rome, Colisée + Vatican, 100€"
        api_key: Clé Gemini de l'agence
        
    Returns:
        {
            "transport_type": "autocar",
            "destination": "Rome, Italie",
            "is_day_trip": false,
            "activities": ["Colisée", "Vatican"],
            "price": 100,
            "hotel_name": null,
            "estimated_duration": 3
        }
    """
    
    model = init_gemini(api_key)
    
    system_prompt = """
    Tu es un assistant spécialisé dans l'analyse de demandes de voyages.
    À partir d'une description en langage naturel, extrais et structure les informations.
    
    CHAMPS À EXTRAIRE :
    
    OBLIGATOIRES :
    - destination (string) : ville, pays (format "Ville, Pays")
    - transport_type (string) : "avion" | "train" | "autocar" | "voiture"
    - is_day_trip (boolean) : true si "excursion" ou "journée" ou "day trip" ou "1 jour"
    
    OPTIONNELS :
    - hotel_name (string|null) : nom de l'hôtel si mentionné
    - activities (array) : liste des lieux/visites mentionnés
    - price (number|null) : prix par personne si mentionné
    - estimated_duration (number|null) : nombre de jours/nuits
    - departure_city (string|null) : ville de départ si mentionnée
    - num_people (number|null) : nombre de personnes si mentionné
    - stars (number|null) : catégorie hôtel (1-5) selon le budget
    - meal_plan (string|null) : "logement_seul" | "petit_dejeuner" | "demi_pension" | "pension_complete" | "all_in"
    
    RÈGLES D'INTELLIGENCE :
    1. Si budget < 300€ → stars: 2-3, meal_plan: "logement_seul" ou "petit_dejeuner"
    2. Si budget 300-600€ → stars: 3-4, meal_plan: "demi_pension"
    3. Si budget > 600€ → stars: 4-5, meal_plan: "pension_complete" ou "all_in"
    4. Si "autocar" → destination Europe max (< 2000km)
    5. Si "excursion" ou "journée" → is_day_trip: true, estimated_duration: 0
    6. Si mention "3 jours" → estimated_duration: 3
    7. Si mention "week-end" → estimated_duration: 2
    
    EXEMPLES :
    
    Input: "Voyage en autocar à Rome, excursion Colisée + Vatican, 100€"
    Output: {
        "destination": "Rome, Italie",
        "transport_type": "autocar",
        "is_day_trip": false,
        "activities": ["Colisée", "Vatican"],
        "price": 100,
        "hotel_name": null,
        "estimated_duration": 3,
        "stars": 3,
        "meal_plan": "petit_dejeuner"
    }
    
    Input: "Excursion d'une journée à Bruges en autocar, 50€"
    Output: {
        "destination": "Bruges, Belgique",
        "transport_type": "autocar",
        "is_day_trip": true,
        "activities": ["Centre historique de Bruges"],
        "price": 50,
        "hotel_name": null,
        "estimated_duration": 0
    }
    
    Input: "Week-end romantique à Paris, train TGV, hôtel 4 étoiles, 350€"
    Output: {
        "destination": "Paris, France",
        "transport_type": "train",
        "is_day_trip": false,
        "activities": ["Tour Eiffel", "Louvre", "Montmartre"],
        "price": 350,
        "hotel_name": null,
        "estimated_duration": 2,
        "stars": 4,
        "meal_plan": "petit_dejeuner"
    }
    
    Réponds UNIQUEMENT en JSON valide, sans markdown ni texte additionnel.
    """
    
    response = model.generate_content(
        system_prompt + f"\n\nPrompt utilisateur: {prompt}"
    )
    
    # Parser la réponse JSON
    try:
        parsed = json.loads(response.text)
        return parsed
    except json.JSONDecodeError:
        # Fallback en cas d'erreur de parsing
        return {
            "error": "Impossible de parser le prompt. Veuillez reformuler.",
            "raw_response": response.text
        }

def generate_day_trip_program(destination: str, activities: list, 
                              departure_time: str, return_time: str,
                              api_key: str) -> list:
    """
    Génère un programme détaillé pour une excursion d'un jour
    
    Returns:
        [
            {"time": "08:00", "activity": "Départ de Bruxelles"},
            {"time": "10:00", "activity": "Pause café"},
            ...
        ]
    """
    model = init_gemini(api_key)
    
    prompt = f"""
    Crée un programme horaire détaillé pour une excursion d'un jour à {destination}.
    
    Activités à inclure : {', '.join(activities)}
    Heure de départ : {departure_time}
    Heure de retour : {return_time}
    
    Le programme doit être réaliste et inclure :
    - Temps de trajet
    - Pauses (café, déjeuner)
    - Temps de visite pour chaque activité
    - Temps libre
    
    Format de sortie : JSON array avec {"time": "HH:MM", "activity": "Description"}
    
    Exemple :
    [
        {{"time": "08:00", "activity": "Départ de Bruxelles"}},
        {{"time": "10:00", "activity": "Pause café"}},
        {{"time": "11:30", "activity": "Arrivée à Rome"}},
        ...
    ]
    
    Réponds UNIQUEMENT en JSON valide.
    """
    
    response = model.generate_content(prompt)
    
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        # Programme par défaut si erreur
        return [
            {"time": departure_time, "activity": f"Départ"},
            {"time": "12:00", "activity": f"Arrivée à {destination}"},
            {"time": "14:00", "activity": "Visites guidées"},
            {"time": "17:00", "activity": "Temps libre"},
            {"time": return_time, "activity": "Retour"}
        ]
```

###### **services/api_gatherer.py** (À COMPLÉTER)

```python
"""
Rassemble les données depuis les APIs externes
(Google Places, YouTube, etc.)
"""

def gather_trip_data(form_data: dict, agency_config: dict) -> dict:
    """
    Collecte toutes les données nécessaires pour la fiche
    
    Args:
        form_data: Données du wizard
        agency_config: Config de l'agence (clés API déchiffrées)
        
    Returns:
        {
            "success": true,
            "api_data": {
                "photos": [...],
                "videos": [...],
                "reviews": {...},
                "attractions": {...}
            },
            "form_data": {...},
            "margin": 123,
            "savings": 456
        }
    """
    pass  # À implémenter (utiliser le code existant de l'ancien projet)
```

###### **services/template_engine.py** (À COMPLÉTER)

```python
"""
Génère les templates HTML des fiches de voyage
"""

def render_trip_template(data: dict, template_type: str, style: str) -> str:
    """
    Génère le HTML final
    
    Args:
        data: Toutes les données du voyage
        template_type: "standard" | "day_trip"
        style: "classic" | "modern" | "luxury"
        
    Returns:
        HTML complet (string)
    """
    pass  # À implémenter
```

##### **5. Frontend - JavaScript Wizard**

###### **Structure de Classe**

```javascript
// /static/js/wizard.js

class TravelWizard {
    constructor() {
        this.currentStep = 0;
        this.totalSteps = 0;
        this.wizardData = {};
        this.parsedPrompt = null;
        this.steps = [];
    }
    
    // Méthodes principales
    async startWizard() { }
    generateSteps(parsedData) { }
    showStep(stepIndex) { }
    renderStep(step) { }
    nextStep() { }
    prevStep() { }
    saveCurrentStep() { }
    async generateTrip() { }
    
    // Renderers par type d'étape
    renderHotelStep(step) { }
    renderDestinationStep(step) { }
    renderActivitiesStep(step) { }
    renderTransportStep(step) { }
    renderTripTypeStep(step) { }
    renderScheduleStep(step) { }
    renderDatesStep(step) { }
    renderPricingStep(step) { }
    renderSummaryStep() { }
    
    // Utilitaires
    initStepListeners(step) { }
    initHotelAutocomplete() { }
    addActivity() { }
    removeActivity(index) { }
}
```

###### **Logique de Génération d'Étapes**

```javascript
generateSteps(parsedData) {
    let steps = [];
    
    // Étapes communes
    if (!parsedData.is_day_trip) {
        steps.push({ id: 'hotel', title: '🏨 Quel hôtel ?' });
    }
    
    steps.push(
        { id: 'destination', title: '📍 Destination' },
        { id: 'activities', title: '🎯 Lieux d\'intérêt' },
        { id: 'transport', title: '🚌 Transport' }
    );
    
    // Si autocar : étape supplémentaire
    if (parsedData.transport_type === 'autocar') {
        steps.push({ id: 'bus_info', title: '📍 Infos Autocar' });
    }
    
    // Type de séjour
    steps.push({ id: 'trip_type', title: '📅 Type de séjour' });
    
    // Étapes conditionnelles
    if (parsedData.is_day_trip) {
        steps.push(
            { id: 'schedule', title: '⏰ Horaires' },
            { id: 'program', title: '📋 Programme' },
            { id: 'pricing', title: '💰 Prix & Inclus' }
        );
    } else {
        steps.push(
            { id: 'dates', title: '🗓️ Dates' },
            { id: 'stars', title: '⭐ Catégorie' },
            { id: 'meal_plan', title: '🍽️ Formule' },
            { id: 'pricing', title: '💰 Prix' }
        );
    }
    
    steps.push({ id: 'summary', title: '✅ Récap' });
    
    return steps;
}
```

##### **6. Templates Frontend**

###### **Base : `/templates/agency/generate.html`**

Structure complète avec :
- Toggle Mode IA / Mode Manuel
- Container du Wizard
- Barre de progression
- Navigation (Retour/Passer/Suivant)
- Modals (résultats, client)

###### **CSS : `/static/css/wizard.css`**

Styles pour :
- Cards d'étapes
- Barre de progression
- Boutons radio/checkbox stylisés
- Animations de transition
- Timeline du programme (voyage 1 jour)

#### 🚧 À Faire Ensuite (Phase 4 suite)

2. **Dashboard Agence** (`/agency/dashboard`)
   - Vue d'ensemble pour l'agence
   - Statistiques en temps réel
   - Activité récente des vendeurs
   - Quota d'utilisation

3. **Liste des Voyages** (`/agency/trips`)
   - Filtres (status, date, vendeur, type)
   - Actions (publier, assigner, marquer vendu)
   - Export PDF
   - Vue détaillée d'un voyage

4. **Gestion des Clients** (`/agency/clients`)
   - CRUD clients
   - Association aux voyages
   - Historique des achats
   - Recherche/filtres

### 🔜 Phase 5 : Templates & Publication (10 messages)
- 3 templates de fiches différents (classic/modern/luxury)
- Template spécial "Voyage d'un jour"
- Système de publication dynamique
- Personnalisation par agence
- Génération PDF

### 🔜 Phase 6 : Déploiement Railway (8 messages)
- Configuration multi-domaines
- Variables d'environnement
- Tests finaux
- Documentation déploiement

## 🎨 ROUTES ACTUELLES

### Authentification
- `GET/POST /login` : Connexion
- `GET /logout` : Déconnexion

### Public
- `GET /` : Redirection selon rôle
- `GET /init` : Page d'initialisation (première installation)

### Super-Admin
- `GET /super-admin` : Dashboard
- `GET /super-admin/agencies` : Page gestion agences
- `GET /super-admin/agencies/<id>/users` : Gestion utilisateurs agence

### API Super-Admin
- `GET /api/super-admin/agencies` : Liste agences
- `POST /api/super-admin/agencies` : Créer agence
- `GET /api/super-admin/agencies/<id>` : Détails agence
- `PUT /api/super-admin/agencies/<id>` : Modifier agence
- `DELETE /api/super-admin/agencies/<id>` : Supprimer agence
- `GET /api/super-admin/agencies/<id>/users` : Liste utilisateurs d'une agence
- `POST /api/super-admin/agencies/<id>/users` : Créer utilisateur
- `GET /api/super-admin/users/<id>` : Détails utilisateur
- `PUT /api/super-admin/users/<id>` : Modifier utilisateur
- `DELETE /api/super-admin/users/<id>` : Supprimer utilisateur

### 🔥 Agency (À CRÉER - Phase 4)
- `GET /agency/dashboard` : Dashboard de l'agence
- `GET /agency/generate` : Page de génération avec Wizard IA
- `GET /agency/trips` : Liste des voyages
- `GET /agency/clients` : Gestion des clients

### 🔥 API Agency (À CRÉER - Phase 4)
- `POST /api/ai-parse-prompt` : Parse un prompt avec Gemini
- `POST /api/generate-preview` : Génère la fiche (appels API)
- `POST /api/render-html-preview` : Render le HTML final
- `GET /api/trips` : Liste des voyages
- `POST /api/trips` : Sauvegarder un voyage
- `GET /api/clients` : Liste des clients
- `POST /api/clients` : Créer un client

## 🔧 CONFIGURATION (.env)

```env
# Sécurité
SECRET_KEY=your-secret-key-change-in-production
MASTER_ENCRYPTION_KEY=your-master-encryption-key-NEVER-CHANGE

# Base de données
DATABASE_URL=sqlite:///odyssee.db  # ou postgres:// en prod

# Super Admin (création initiale)
SUPER_ADMIN_USERNAME=superadmin
SUPER_ADMIN_PASSWORD=ChangeMe2025!
SUPER_ADMIN_EMAIL=admin@odyssee-saas.com

# Flask
FLASK_ENV=development
FLASK_DEBUG=1

# 🔥 NOUVEAU - APIs (optionnel, peut être configuré par agence)
GOOGLE_PLACES_API_KEY=your-google-places-key
GOOGLE_GEMINI_API_KEY=your-gemini-key
YOUTUBE_API_KEY=your-youtube-key
```

## 💻 COMMANDES UTILES

### Initialisation
```bash
# Créer la base de données + super-admin
flask init-db

# Lancer l'application
flask run

# Créer une agence de test (script helper)
python create_agency.py
```

### Développement
```bash
# Installation des dépendances
pip install -r requirements.txt          # Production
pip install -r requirements-light.txt    # Mac (sans psycopg2)

# Ajouter les nouvelles dépendances IA
pip install google-generativeai

# Migrations (si modifications des modèles)
flask db init                            # Première fois seulement
flask db migrate -m "Add trip fields for bus and day trips"
flask db upgrade
```

## 🎯 ÉTAT ACTUEL DU PROJET

### ✅ Phase 3 : Interface Super-Admin (TERMINÉE - 100%)
- Connexion super-admin
- Création d'agence via interface
- Modification d'agence (avec préservation des données)
- Suppression d'agence (avec protection)
- Toggle actif/inactif pour agences
- Chiffrement/déchiffrement des clés API
- Gestion complète des utilisateurs
- Création d'admins d'agence et de vendeurs
- Modification des quotas et permissions
- Suppression intelligente des utilisateurs
- Interface responsive avec Tailwind

### 🚀 Phase 4 : Interface Agence - Backend (EN COURS - 60%)

#### ✅ Fichiers Backend Créés (14 Oct 2025) :

1. **services/ai_assistant.py** ✅ COMPLET
   - Classe `AIAssistant` avec Gemini API
   - `parse_travel_prompt()` - Parse les prompts en langage naturel
   - `generate_day_trip_program()` - Génère programmes excursions
   - `suggest_activities()` - Suggère activités par destination
   - `estimate_travel_duration()` - Estime durées de trajet
   - Validation et nettoyage des données
   - Tests inclus
   - 📄 **420 lignes** de code production-ready

2. **app.py** ✅ COMPLET - VERSION MISE À JOUR
   - Nouveau décorateur `@agency_required`
   - 3 fonctions helper (quotas, durée)
   - 4 routes pages agence :
     * `/agency/dashboard`
     * `/agency/generate` (Wizard IA)
     * `/agency/trips`
     * `/agency/clients`
   - 7 routes API :
     * `/api/ai-parse-prompt`
     * `/api/generate-preview`
     * `/api/render-html-preview`
     * `/api/trips` (GET/POST)
     * `/api/clients` (GET/POST)
     * `/api/ai-generate-program`
   - Gestion des quotas intégrée
   - 📄 **950+ lignes** (vs 601 avant)

#### 🚧 À Créer (Frontend - Phase 4 suite) :

3. **templates/agency/generate.html**
   - Page complète du Wizard IA
   - Mode IA + Mode Manuel
   - Barre de progression
   - Modals (client, résultats)
   - ~500 lignes HTML

4. **static/js/wizard.js**
   - Classe `TravelWizard`
   - Génération dynamique des étapes
   - Renderers par type d'étape
   - Gestion navigation
   - ~800 lignes JavaScript

5. **static/css/wizard.css**
   - Styles du wizard
   - Animations
   - Responsive design
   - ~300 lignes CSS

6. **templates/agency/dashboard.html**
   - Dashboard agence (simple)
   - Statistiques
   - ~200 lignes HTML

7. **templates/agency/trips.html**
   - Liste des voyages
   - Filtres basiques
   - ~250 lignes HTML

8. **templates/agency/clients.html**
   - Gestion clients
   - CRUD interface
   - ~200 lignes HTML

### 🧪 Données de test actuelles :
- 1 super-admin créé
- 1+ agence(s) de test créée(s)
- Utilisateurs test créés pour les agences
- Base de données SQLite locale

### 🐛 Bugs connus :
- Aucun bug majeur détecté
- ⚠️ AI Assistant nécessite installation de `google-generativeai`

## 📝 PROCHAINES ÉTAPES IMMÉDIATES

### 🔥 PRIORITÉ ABSOLUE (Phase 4 - Suite Frontend) :

#### ✅ Backend Terminé (14 Oct 2025) :
- ✅ Service IA (`ai_assistant.py`) - 420 lignes
- ✅ Routes Flask dans `app.py` - 10 nouvelles routes
- ✅ Décorateurs et helpers
- ✅ Gestion des quotas

#### 🚧 Frontend à Créer (Prochaine session) :

**1. Créer le Wizard JavaScript**
   - 🚧 Créer `/static/js/wizard.js` (~800 lignes)
   - Classe `TravelWizard` complète
   - Génération dynamique des étapes
   - Renderers par type
   - Navigation et validation

**2. Créer la Page HTML de Génération**
   - 🚧 Créer `/templates/agency/generate.html` (~500 lignes)
   - Interface Wizard complète
   - Mode IA + Mode Manuel
   - Barre de progression
   - Modals

**3. Créer les Styles**
   - 🚧 Créer `/static/css/wizard.css` (~300 lignes)
   - Styles wizard
   - Animations
   - Responsive

**4. Créer Dashboard Agence Simple**
   - 🚧 `/templates/agency/dashboard.html`
   - Statistiques de base
   - Liens rapides

**5. Tester le Système Complet**
   - Installer dépendances (`google-generativeai`)
   - Créer agence test avec clé Gemini
   - Tester parsing de prompts
   - Tester génération complète
   - Vérifier quotas

### 📋 Installation Nécessaire :

```bash
# 1. Installer la dépendance Gemini
pip install google-generativeai

# 2. Remplacer app.py
cp app_complete.py app.py

# 3. Créer dossier services
mkdir -p services
touch services/__init__.py

# 4. Copier ai_assistant.py
cp ai_assistant.py services/

# 5. Migrer la base de données (nouveaux champs Trip)
flask db migrate -m "Add trip fields for day trips and bus travel"
flask db upgrade

# 6. Tester
flask run
```

### Méthode de travail :
- **Toujours créer des artifacts complets** (copier-coller direct)
- Tester après chaque ajout
- Valider avant de passer à la suite
- Documenter les changements dans ce fichier

## 📚 NOTES IMPORTANTES

### Multi-Tenant
- Identification par sous-domaine via middleware
- Isolation complète des données par agence
- Super-admin voit tout, agency_admin voit son agence, seller voit ses données

### Sécurité
- Mots de passe : Hash bcrypt
- Clés API : Chiffrement Fernet
- Sessions : Cookie HTTP-only
- Clés API par agence (Google, Gemini, Stripe)

### Base de Données
- SQLite en dev (fichier odyssee.db)
- PostgreSQL prévu en prod (Railway)
- Migrations Alembic pour les modifications
- 🔥 NOUVEAU : Ajouter champs Trip (is_day_trip, transport_type, bus_departure_address, etc.)

### Intelligence Artificielle
- Gemini API pour parsing de prompts
- Pré-remplissage intelligent du wizard
- Génération de programmes automatiques
- Suggestions contextuelles

### Types de Voyages Supportés
1. **Voyage Standard** : Avion/Train, hôtel, plusieurs jours
2. **Voyage Autocar** : Point de départ, durée trajet, plusieurs jours
3. **Excursion d'un Jour** : Autocar, horaires, programme, sans hôtel

## 🔗 RESSOURCES

### Documentation utilisée :
- Flask : https://flask.palletsprojects.com/
- SQLAlchemy : https://www.sqlalchemy.org/
- Cryptography : https://cryptography.io/
- Tailwind CSS : https://tailwindcss.com/
- Google Gemini API : https://ai.google.dev/
- Google Places API : https://developers.google.com/maps/documentation/places

### Hébergement prévu :
- Railway : https://railway.app/

## 🎓 POUR REPRENDRE UNE CONVERSATION

### Phrase de contexte à donner :
"Je reprends le projet Odyssée SaaS. Phase 3 (Interface Super-Admin) terminée ✅. Phase 4 Backend terminé (60%) : ai_assistant.py + routes Flask créés le 14 Oct 2025. Il reste à créer le frontend : wizard.js, generate.html, CSS, et templates dashboard/trips/clients. Toutes les spécifications sont dans CONTEXTE_PROJET.md. Prêt à créer les fichiers frontend. Méthode : artifacts complets pour copier-coller dans VS Code."

### Documents à fournir :
- CONTEXTE_PROJET_UPDATED.md (ce fichier - version complète)
- app.py (nouveau fichier app_complete.py créé)
- models.py (pour voir les modèles actuels)

### Fichiers Backend Créés (Phase 4 - 14 Oct 2025) :
1. ✅ `/services/ai_assistant.py` (420 lignes) - Service IA complet
2. ✅ `app_complete.py` (950+ lignes) - Routes et décorateurs

### Fichiers Frontend à Créer (Phase 4 - Suite) :
3. 🚧 `/static/js/wizard.js` (~800 lignes) - Logique JavaScript
4. 🚧 `/templates/agency/generate.html` (~500 lignes) - Page Wizard
5. 🚧 `/static/css/wizard.css` (~300 lignes) - Styles
6. 🚧 `/templates/agency/dashboard.html` (~200 lignes) - Dashboard simple
7. 🚧 `/templates/agency/trips.html` (~250 lignes) - Liste voyages
8. 🚧 `/templates/agency/clients.html` (~200 lignes) - Gestion clients

### Commandes d'installation (après création frontend) :
```bash
# 1. Installer dépendance IA
pip install google-generativeai

# 2. Remplacer app.py
cp app_complete.py app.py

# 3. Créer dossier services
mkdir -p services
touch services/__init__.py
cp ai_assistant.py services/

# 4. Migration BDD (nouveaux champs)
flask db migrate -m "Add day trip and bus fields"
flask db upgrade

# 5. Lancer
flask run
```

---

**Dernière mise à jour** : 14 octobre 2025 - 23h15
**État** : Phase 3 terminée ✅ - Phase 4 Backend terminé (60%) 🚀 - Phase 4 Frontend en attente
**Fichiers créés aujourd'hui** : ai_assistant.py (420L), app_complete.py (950L)
**Environnement** : MacOS + VS Code + Python 3.x + Flask
**Prochaine action** : Créer wizard.js + generate.html + CSS pour finaliser le système de génération