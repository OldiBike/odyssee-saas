# 📋 CONTEXTE PROJET ODYSSÉE SAAS - Mise à jour du 14/10/2025

## 🎯 OBJECTIF DU PROJET
Plateforme SaaS multi-tenant permettant à plusieurs agences de voyages de :
- Générer des offres de voyages personnalisées
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
- **Déploiement prévu** : Railway (multi-domaines)

### Structure des Fichiers
```
odyssee-saas/
├── app.py                    # Application Flask principale ✅ COMPLET
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
├── services/                # 🚧 À DÉVELOPPER (Phase 4)
│   ├── api_gatherer.py      # Appels API Google/autres
│   ├── template_engine.py   # Génération fiches voyage
│   └── publication.py       # Upload SFTP/FTP
├── templates/
│   ├── base.html            # Template de base ✅
│   ├── login.html           # Page de connexion ✅
│   ├── home.html            # Page d'accueil ✅
│   └── super_admin/
│       ├── dashboard.html   # Dashboard super-admin ✅
│       └── agencies.html    # Gestion agences ✅ COMPLET (CRUD)
├── static/                  # 🚧 À DÉVELOPPER
│   ├── css/
│   └── js/
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

### ✅ Phase 3 : Interface Super-Admin (EN COURS - 80% FAIT)

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

#### 🚧 À faire (Phase 3) :
3. **Gestion des utilisateurs par agence**
   - Créer des agency_admin pour une agence
   - Créer des sellers pour une agence
   - Modifier/désactiver des utilisateurs
   - Réinitialiser mot de passe

4. **Vue détaillée d'une agence**
   - Page dédiée avec onglets
   - Liste des utilisateurs
   - Liste des voyages
   - Statistiques détaillées
   - Logs d'activité

5. **Configuration avancée**
   - Test de validité des clés API
   - Gestion des quotas en temps réel
   - Historique des modifications

### 🔜 Phase 4 : Interface Agence (15 messages)
- Génération de voyages (système existant à intégrer)
- Dashboard vendeurs
- Gestion clients
- Statistiques par agence

### 🔜 Phase 5 : Templates & Publication (10 messages)
- 3 templates de fiches différents (classic/modern/luxury)
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

### API Super-Admin
- `GET /api/super-admin/agencies` : Liste agences
- `POST /api/super-admin/agencies` : Créer agence
- `GET /api/super-admin/agencies/<id>` : Détails agence
- `PUT /api/super-admin/agencies/<id>` : Modifier agence
- `DELETE /api/super-admin/agencies/<id>` : Supprimer agence

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

# Migrations (si modifications des modèles)
flask db init                            # Première fois seulement
flask db migrate -m "Description"        # Créer une migration
flask db upgrade                         # Appliquer les migrations
```

## 🎯 ÉTAT ACTUEL DU PROJET

### ✅ Fonctionnalités testées et validées :
- Connexion super-admin
- Création d'agence via interface
- Modification d'agence (avec préservation des données)
- Suppression d'agence (avec protection)
- Toggle actif/inactif
- Chiffrement/déchiffrement des clés API
- Interface responsive avec Tailwind

### 🧪 Données de test actuelles :
- 1 super-admin créé
- 1 agence de test créée
- Base de données SQLite locale

### 🐛 Bugs connus :
- Aucun bug majeur détecté pour le moment

## 📝 PROCHAINES ÉTAPES

### Immédiatement (Suite Phase 3) :
1. **Créer la gestion des utilisateurs**
   - Route : `/super-admin/agencies/<id>/users`
   - API : CRUD pour User
   - Interface : Liste + Modal création/édition

2. **Créer la vue détaillée d'une agence**
   - Route : `/super-admin/agencies/<id>`
   - Onglets : Infos, Utilisateurs, Voyages, Stats

### Méthode de travail :
- **Toujours créer des artifacts complets** (copier-coller direct)
- Tester après chaque ajout
- Valider avant de passer à la suite

## 📚 NOTES IMPORTANTES

### Multi-Tenant
- Identification par sous-domaine via middleware
- Isolation complète des données par agence
- Super-admin voit tout, agency_admin voit son agence, seller voit ses données

### Sécurité
- Mots de passe : Hash bcrypt
- Clés API : Chiffrement Fernet
- Sessions : Cookie HTTP-only

### Base de Données
- SQLite en dev (fichier odyssee.db)
- PostgreSQL prévu en prod (Railway)
- Migrations Alembic pour les modifications

## 🔗 RESSOURCES

### Documentation utilisée :
- Flask : https://flask.palletsprojects.com/
- SQLAlchemy : https://www.sqlalchemy.org/
- Cryptography : https://cryptography.io/
- Tailwind CSS : https://tailwindcss.com/

### Hébergement prévu :
- Railway : https://railway.app/

## 🎓 POUR REPRENDRE UNE CONVERSATION

### Phrase de contexte à donner :
"Je reprends le projet Odyssée SaaS. Nous sommes en Phase 3 (Interface Super-Admin). Le CRUD des agences est terminé et fonctionne. Prochaine étape : créer la gestion des utilisateurs par agence. Utilise le fichier CONTEXTE_PROJET.md pour avoir tous les détails. Méthode : toujours créer des artifacts complets pour copier-coller dans VS Code."

### Documents à fournir :
- Ce fichier (CONTEXTE_PROJET.md)
- app.py (si modifications nécessaires)
- models.py (référence)
- Le dernier template HTML en cours de travail

---

**Dernière mise à jour** : 14 octobre 2025
**État** : Phase 3 en cours (CRUD Agences ✅, Gestion Utilisateurs 🚧)
**Environnement** : MacOS + VS Code + Python 3.x + Flask
