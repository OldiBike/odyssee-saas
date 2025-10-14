# 📋 CONTEXTE PROJET ODYSSÉE SAAS - Mise à jour du 14/10/2025 23h30

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
├── app.py                    # ✅ REMPLACÉ (14 Oct) - 950+ lignes
├── models.py                 # ✅ COMPLET (nécessite migration)
├── config.py                 # ✅ COMPLET
├── requirements.txt          # ✅ + google-generativeai
├── requirements-light.txt    # ✅ Version Mac sans psycopg2
├── .env                      # Variables d'environnement (NON COMMITÉ)
├── .gitignore               # ✅ COMPLET
├── create_agency.py         # Script helper ✅
├── utils/
│   ├── __init__.py          # ✅
│   └── crypto.py            # Système de chiffrement ✅ COMPLET
├── services/                # ✅ Phase 4 - Backend CRÉÉ
│   ├── __init__.py          # ✅ À créer (fichier vide)
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
│   └── agency/              # ✅ Phase 4 - Frontend CRÉÉ
│       ├── generate.html    # ✅ CRÉÉ (14 Oct) - 567 lignes - Wizard IA
│       ├── dashboard.html   # 🚧 À créer (~200 lignes)
│       ├── trips.html       # 🚧 À créer (~250 lignes)
│       └── clients.html     # 🚧 À créer (~200 lignes)
├── static/
│   ├── css/
│   │   └── wizard.css       # 🚧 À créer (~300 lignes) - OPTIONNEL
│   └── js/
│       └── wizard.js        # ✅ CRÉÉ (14 Oct) - 1092 lignes
└── migrations/              # ⚠️ À GÉNÉRER (nouveaux champs Trip)
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

### Trip (Voyage) ⚠️ NÉCESSITE MIGRATION
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
- ✅ NOUVEAUX CHAMPS (à ajouter via migration) :
  - is_day_trip (bool) : True si excursion d'un jour
  - transport_type (str) : "avion" | "train" | "autocar" | "voiture"
  - bus_departure_address (text, nullable) : Point de départ autocar
  - travel_duration_minutes (int, nullable) : Durée trajet en minutes
  - departure_time (time, nullable) : Heure départ (voyage 1 jour)
  - return_time (time, nullable) : Heure retour (voyage 1 jour)
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
  - `@agency_required` : Agency admin ou seller (NOUVEAU - Phase 4)

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

### ✅ Phase 3 : Interface Super-Admin (TERMINÉE - 100%)

#### Complété :
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

3. **Gestion des utilisateurs par agence**
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

### 🔥 Phase 4 : Interface Agence (EN COURS - 85% COMPLÉTÉ)

#### ✅ Fichiers Backend Créés (14 Oct 2025 - 23h30) :

**1. services/ai_assistant.py** ✅ COMPLET (420 lignes)
   - Classe `AIAssistant` avec Gemini API
   - `parse_travel_prompt()` - Parse les prompts en langage naturel
   - `generate_day_trip_program()` - Génère programmes excursions
   - `suggest_activities()` - Suggère activités par destination
   - `estimate_travel_duration()` - Estime durées de trajet
   - Validation et nettoyage des données
   - Gestion des erreurs robuste
   - Tests inclus en bas du fichier

**2. app.py** ✅ COMPLET (950+ lignes)
   - **Imports ajoutés** : `import json`, `from datetime import timedelta`
   - **Nouveau décorateur** : `@agency_required`
   - **3 fonctions helper** :
     * `check_generation_quota(user, agency)` - Vérifie quotas
     * `increment_generation_counters(user, agency)` - Incrémente compteurs
     * `calculate_duration_minutes(data)` - Calcule durée trajet
   
   - **4 routes pages agence** :
     * `GET /agency/dashboard` - Dashboard agence
     * `GET /agency/generate` - Page génération avec Wizard IA ⭐
     * `GET /agency/trips` - Liste des voyages
     * `GET /agency/clients` - Gestion des clients
   
   - **7 routes API** :
     * `POST /api/ai-parse-prompt` - Parse prompt avec Gemini
     * `POST /api/generate-preview` - Génère aperçu voyage
     * `POST /api/render-html-preview` - Render HTML final
     * `GET/POST /api/trips` - CRUD voyages
     * `GET/POST /api/clients` - CRUD clients
     * `POST /api/ai-generate-program` - Génère programme excursion
   
   - **Modifications route home** : Redirige vers `agency_dashboard`
   - Gestion des quotas intégrée
   - Gestion des erreurs complète

**3. static/js/wizard.js** ✅ COMPLET (1092 lignes)
   - **Classe TravelWizard** complète
   - **12 méthodes de rendu** (une par étape) :
     * `renderHotelStep()` - Hôtel
     * `renderDestinationStep()` - Destination
     * `renderActivitiesStep()` - Lieux d'intérêt (ajout/suppression)
     * `renderTransportStep()` - Transport (avec champs autocar)
     * `renderTripTypeStep()` - Type de séjour (jour/multi-jours)
     * `renderScheduleStep()` - Horaires (excursion)
     * `renderProgramStep()` - Programme (génération IA)
     * `renderDatesStep()` - Dates séjour
     * `renderStarsStep()` - Catégorie hôtel
     * `renderMealPlanStep()` - Formule repas
     * `renderPricingStep()` - Prix & services
     * `renderSummaryStep()` - Récapitulatif final
   
   - **Fonctionnalités** :
     * Génération dynamique des étapes selon type voyage
     * Pré-remplissage intelligent depuis parsing IA
     * Validation des champs à chaque étape
     * Navigation fluide (next/prev/skip)
     * Sauvegarde automatique des données
     * Appels API pour génération programme
     * Barre de progression animée
     * Loading overlay
     * Gestion erreurs
     * Support voyage 1 jour vs séjour
     * Support autocar avec champs spécifiques

**4. templates/agency/generate.html** ✅ COMPLET (567 lignes) - ⚠️ VERSION CORRIGÉE
   - **Base template** : Extend `base.html`
   - **Styles CSS inline** : ~400 lignes de styles (en attendant wizard.css externe)
   - ✅ **Corrections appliquées le 14 Oct 23h45** :
     * Fix CSS : Variables CSS (:root) au lieu de Jinja2 inline
     * Fix JS : Syntaxe {% if %} au lieu de ternaire Jinja2
     * Fix : Gestion sécurisée des variables g.agency
     * Fix : userMargin en valeur fixe (80) - récupéré côté serveur
   - **Structure complète** :
     * Étape 0 : Choix mode IA / Manuel
     * Tabs de sélection
     * Zone prompt avec textarea
     * 4 exemples de prompts cliquables
     * Bouton "Démarrer le Wizard"
     * Container wizard (étapes dynamiques)
     * Barre de progression
     * Boutons navigation (Retour/Passer/Suivant)
     * Loading overlay avec spinner
   
   - **Intégrations** :
     * Google Places API (autocomplete) - chargement conditionnel
     * wizard.js
     * Variables Jinja2 sécurisées
     * Configuration globale JS : `window.WIZARD_CONFIG`
   
   - **Design** :
     * Responsive (mobile-first)
     * Animations CSS
     * Branding dynamique (couleur agence via CSS variables)
     * Interface moderne et claire

#### 🚧 À Créer (Frontend restant - Phase 4) :

**5. static/css/wizard.css** (OPTIONNEL - ~300 lignes)
   - Externaliser les styles de generate.html
   - Améliorer la maintenabilité
   - Ajouter animations supplémentaires
   - Note : Pas obligatoire car styles déjà inline dans generate.html

**6. templates/agency/dashboard.html** (~200 lignes)
   - Dashboard simple avec statistiques
   - Liens rapides vers Generate/Trips/Clients
   - Graphiques basiques (optionnel)
   - Affichage quotas

**7. templates/agency/trips.html** (~250 lignes)
   - Liste des voyages (tableau)
   - Filtres : status, date, vendeur, type
   - Actions : voir détails, publier, assigner, marquer vendu
   - Pagination

**8. templates/agency/clients.html** (~200 lignes)
   - Liste des clients (tableau)
   - CRUD interface : ajouter, modifier, supprimer
   - Recherche et filtres
   - Historique des voyages par client

### 🔜 Phase 5 : Templates & Publication (Future)
- 3 templates de fiches différents (classic/modern/luxury)
- Template spécial "Voyage d'un jour"
- Système de publication dynamique
- Personnalisation par agence
- Génération PDF

### 🔜 Phase 6 : Déploiement Railway (Future)
- Configuration multi-domaines
- Variables d'environnement
- Tests finaux
- Documentation déploiement

## 🎨 ROUTES ACTUELLES

### Authentification
- `GET/POST /login` : Connexion
- `GET /logout` : Déconnexion

### Public
- `GET /` : Redirection selon rôle (vers agency_dashboard ou super_admin_dashboard)
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

### 🔥 Agency - Pages (NOUVEAU - Phase 4)
- `GET /agency/dashboard` : Dashboard de l'agence
- `GET /agency/generate` : Page de génération avec Wizard IA ⭐
- `GET /agency/trips` : Liste des voyages
- `GET /agency/clients` : Gestion des clients

### 🔥 API Agency (NOUVEAU - Phase 4)
- `POST /api/ai-parse-prompt` : Parse un prompt avec Gemini
- `POST /api/generate-preview` : Génère la fiche (appels API)
- `POST /api/render-html-preview` : Render le HTML final
- `GET /api/trips` : Liste des voyages
- `POST /api/trips` : Sauvegarder un voyage
- `GET /api/clients` : Liste des clients
- `POST /api/clients` : Créer un client
- `POST /api/ai-generate-program` : Génère programme excursion

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

# ✅ NOUVEAU - APIs IA (optionnel, peut être configuré par agence)
GOOGLE_PLACES_API_KEY=your-google-places-key
GOOGLE_GEMINI_API_KEY=your-gemini-key
YOUTUBE_API_KEY=your-youtube-key
```

## 💻 COMMANDES & INSTALLATION

### Installation Initiale
```bash
# Créer la base de données + super-admin
flask init-db

# Lancer l'application
flask run
```

### ⚠️ INSTALLATION PHASE 4 (À FAIRE) :

```bash
# 1. Installer la dépendance IA
pip install google-generativeai

# 2. Remplacer app.py
cp app_complete.py app.py

# 3. Créer dossier services
mkdir -p services
touch services/__init__.py

# 4. Copier ai_assistant.py
cp ai_assistant.py services/

# 5. Créer dossiers static
mkdir -p static/js
mkdir -p static/css

# 6. Copier wizard.js
cp wizard.js static/js/

# 7. Créer dossier templates/agency
mkdir -p templates/agency

# 8. Copier generate.html
cp generate.html templates/agency/

# 9. ⚠️ IMPORTANT : Migration BDD (nouveaux champs Trip)
flask db migrate -m "Add trip fields for day trips and bus travel"
flask db upgrade

# 10. Tester
flask run
```

### Migrations (si modifications des modèles)
```bash
flask db init                            # Première fois seulement
flask db migrate -m "Description"        # Créer migration
flask db upgrade                         # Appliquer migration
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

### 🚀 Phase 4 : Interface Agence (EN COURS - 85%)

#### ✅ Backend Complet (100%) :
- ✅ Service IA (`ai_assistant.py`) - 420 lignes
- ✅ Routes Flask dans `app.py` - 10 nouvelles routes + décorateurs
- ✅ Décorateur `@agency_required`
- ✅ Gestion des quotas (quotidien + mensuel)
- ✅ Helper functions

#### ✅ Frontend Wizard (95%) :
- ✅ JavaScript complet (`wizard.js`) - 1092 lignes
- ✅ Page HTML (`generate.html`) - 567 lignes
- ✅ Styles CSS inline dans generate.html
- ⚪ CSS externe (`wizard.css`) - OPTIONNEL

#### 🚧 Frontend Complémentaire (0%) :
- ⏳ Dashboard agence (`dashboard.html`)
- ⏳ Liste voyages (`trips.html`)
- ⏳ Gestion clients (`clients.html`)

### 📊 Statistiques des Fichiers Créés (14 Oct 2025) :

| Fichier | Lignes | Emplacement | État |
|---------|--------|-------------|------|
| `ai_assistant.py` | 420 | `services/` | ✅ Complet |
| `app_complete.py` | 950+ | racine (remplace app.py) | ✅ Complet |
| `wizard.js` | 1092 | `static/js/` | ✅ Complet |
| `generate.html` | 567 | `templates/agency/` | ✅ Complet |
| **TOTAL CRÉÉ** | **3029+** | | **85% Phase 4** |

### 📋 Fichiers Restants à Créer :

| Fichier | Lignes | Priorité | État |
|---------|--------|----------|------|
| `wizard.css` | ~300 | 🟡 Optionnel | Styles déjà inline |
| `dashboard.html` | ~200 | 🔴 Haute | À créer |
| `trips.html` | ~250 | 🔴 Haute | À créer |
| `clients.html` | ~200 | 🔴 Haute | À créer |
| **TOTAL RESTANT** | **~950** | | **15% Phase 4** |

### 🧪 Données de test actuelles :
- 1 super-admin créé
- 1+ agence(s) de test créée(s)
- Utilisateurs test créés pour les agences
- Base de données SQLite locale

### 🐛 Bugs connus :
- Aucun bug majeur détecté
- ⚠️ AI Assistant nécessite installation de `google-generativeai`
- ⚠️ Migration BDD nécessaire pour nouveaux champs Trip
- ✅ **Bugs corrigés le 14 Oct 23h45** :
  * Erreurs Jinja2 dans generate.html (CSS + JavaScript)
  * Variables CSS au lieu de Jinja2 inline dans les styles
  * Configuration JavaScript simplifiée et sécurisée

## 📝 PROCHAINES ÉTAPES IMMÉDIATES

### 🔥 PHASE 4 - Finalisation (15% restant) :

**1. Installation et Test du Wizard** 🧪
   - [ ] Installer `google-generativeai`
   - [ ] Copier les 4 fichiers aux bons emplacements
   - [ ] Créer `services/__init__.py` (vide)
   - [ ] Migrer la base de données (nouveaux champs)
   - [ ] Créer une agence test avec clé Gemini
   - [ ] Tester le parsing de prompts
   - [ ] Tester génération complète voyage standard
   - [ ] Tester génération voyage d'un jour
   - [ ] Tester transport autocar
   - [ ] Vérifier les quotas

**2. Créer Pages Complémentaires** 📄
   - [ ] `dashboard.html` - Dashboard simple avec stats
   - [ ] `trips.html` - Liste voyages avec filtres
   - [ ] `clients.html` - Gestion clients CRUD
   - [ ] (Optionnel) `wizard.css` - Externaliser styles

**3. Tests d'Intégration** ✅
   - [ ] Tester le flow complet : prompt → wizard → génération → sauvegarde
   - [ ] Tester les permissions (seller vs agency_admin)
   - [ ] Tester les quotas (dépassement)
   - [ ] Tester voyage 1 jour vs séjour
   - [ ] Tester autocar vs autres transports

### 📋 Commandes d'Installation Complètes :

```bash
# === ÉTAPE 1 : BACKUP ===
cp app.py app.py.backup
cp -r templates templates.backup

# === ÉTAPE 2 : INSTALLER DÉPENDANCES ===
pip install google-generativeai

# === ÉTAPE 3 : CRÉER STRUCTURE ===
mkdir -p services
mkdir -p static/js
mkdir -p static/css
mkdir -p templates/agency

# === ÉTAPE 4 : COPIER LES FICHIERS ===
# Backend
cp app_complete.py app.py
cp ai_assistant.py services/
touch services/__init__.py

# Frontend
cp wizard.js static/js/
cp generate.html templates/agency/

# === ÉTAPE 5 : MIGRATION BDD ===
flask db migrate -m "Add trip fields for day trips and bus travel"
flask db upgrade

# === ÉTAPE 6 : TESTER ===
flask run

# Accéder à : http://localhost:5000
# Se connecter avec un vendeur
# Aller sur /agency/generate
```

### 🎯 Ordre de Priorité :

1. **🔥 CRITIQUE** : Installation + Migration + Test du Wizard
2. **🔴 HAUTE** : Dashboard agence (pour navigation)
3. **🟠 MOYENNE** : Liste voyages + Clients
4. **🟡 BASSE** : Externalisation CSS

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
- ⚠️ MIGRATION NÉCESSAIRE : Ajouter champs Trip (is_day_trip, transport_type, etc.)

### Intelligence Artificielle
- Gemini API pour parsing de prompts
- Pré-remplissage intelligent du wizard
- Génération de programmes automatiques
- Suggestions contextuelles
- Validation et nettoyage des données

### ✅ Corrections Techniques (14 Oct 23h45)
**Problème initial** : Erreurs Jinja2 dans `generate.html`
- ❌ Variables Jinja2 directement dans CSS : `color: {{ g.agency.primary_color }}`
- ❌ Syntaxe ternaire Jinja2 dans JavaScript : `{{ var if cond else default }}`

**Solutions appliquées** :
1. **CSS Variables** : Utilisation de `:root` et `var(--primary-color)`
   ```css
   :root {
       --primary-color: {{ g.agency.primary_color }};
   }
   .btn { background: var(--primary-color); }
   ```

2. **Configuration JavaScript sécurisée** :
   ```javascript
   agencyName: "{% if g.agency %}{{ g.agency.name }}{% else %}Agence{% endif %}"
   ```

3. **Variables par défaut** :
   - `userMargin: 80` (fixe, récupéré côté serveur lors génération)
   - Gestion sécurisée de `g.agency` avec fallbacks

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

### Phrase de contexte à donner à Claude :
```
Je reprends le projet Odyssée SaaS. 
Phase 3 (Interface Super-Admin) terminée ✅ 
Phase 4 (Interface Agence) à 85% : 
- Backend complet : ai_assistant.py (420L) + app.py (950L) ✅
- Frontend Wizard : wizard.js (1092L) + generate.html (567L - VERSION CORRIGÉE) ✅
- Bugs Jinja2 résolus (CSS variables + config JS simplifiée) ✅
- Restant : dashboard.html, trips.html, clients.html

Tous les fichiers créés le 14 Oct 2025 (corrections 23h45).
Prêt à créer les pages complémentaires ou à tester le wizard.
Méthode : artifacts complets copier-coller.
```

### Documents à fournir à Claude :
1. **CONTEXTE_PROJET_FINAL.md** (ce fichier)
2. **app.py** (si besoin de modifier)
3. **models.py** (si besoin de voir la structure)

### Fichiers Backend Créés (Phase 4) :
| Fichier | Taille | Emplacement | Créé le |
|---------|--------|-------------|---------|
| `ai_assistant.py` | 420L | `services/` | 14 Oct 23h00 |
| `app_complete.py` | 950L | racine | 14 Oct 23h10 |
| `wizard.js` | 1092L | `static/js/` | 14 Oct 23h20 |
| `generate.html` | 567L | `templates/agency/` | 14 Oct 23h30 |

### Fichiers à Créer (Phase 4 - Finalisation) :
| Fichier | Taille | Priorité | Temps estimé |
|---------|--------|----------|--------------|
| `dashboard.html` | ~200L | 🔴 Haute | 10 min |
| `trips.html` | ~250L | 🔴 Haute | 15 min |
| `clients.html` | ~200L | 🔴 Haute | 10 min |
| `wizard.css` | ~300L | 🟡 Optionnel | 10 min |

### Commandes Rapides :
```bash
# Installation complète Phase 4
pip install google-generativeai && \
mkdir -p services static/js templates/agency && \
cp app_complete.py app.py && \
cp ai_assistant.py services/ && \
touch services/__init__.py && \
cp wizard.js static/js/ && \
cp generate.html templates/agency/ && \
flask db migrate -m "Add trip fields" && \
flask db upgrade && \
flask run

# Test rapide
curl http://localhost:5000/agency/generate
```

---

**Dernière mise à jour** : 14 octobre 2025 - 23h45
**État** : Phase 3 ✅ | Phase 4 à 85% 🚀 | Backend + Wizard complets + Bugs corrigés
**Fichiers créés** : 4 fichiers, 3029+ lignes de code
**Corrections** : generate.html (CSS variables + config JS)
**Prochaine étape** : Tester le wizard OU créer dashboard/trips/clients
**Environnement** : MacOS + VS Code + Python 3.x + Flask + Gemini API
