# 📋 Contexte du Projet Odyssée

## 🎯 Vue d'ensemble

Ce document sert de référence pour comprendre rapidement l'architecture et l'organisation du projet Odyssée lors de nouvelles conversations.

## 📁 Structure du projet

Le projet Odyssée est divisé en **DEUX applications Flask distinctes** :

### 1. **odyssee-app** (Ancienne version - Single tenant)
- **Localisation** : `../App/` (dossier parent)
- **Fichier principal** : `../App/app.py`
- **Caractéristiques** :
  - Application Flask simple, mono-utilisateur
  - Version originale avec toutes les fonctionnalités de base
  - Sert de **référence** pour les fonctionnalités à migrer
  - Contient des routes et fonctions qui peuvent être copiées/adaptées

### 2. **odyssee-saas** (Nouvelle version - Multi-tenant)
- **Localisation** : `/Users/oldibox/Library/CloudStorage/OneDrive-Personnel/VP/Odyssee` (répertoire actuel)
- **Fichier principal** : `app.py`
- **Caractéristiques** :
  - Application SaaS multi-agences
  - Architecture avancée avec gestion des utilisateurs, rôles, et agences
  - Synchronisation email, CRM, analytics, rapports
  - **Destination** des nouvelles fonctionnalités et migrations

## 🔄 Workflow de migration

Quand on travaille sur une nouvelle fonctionnalité :

1. **Analyser** dans `../App/app.py` (odyssee-app) pour voir si la fonctionnalité existe
2. **Adapter** le code pour le contexte multi-tenant (agences, utilisateurs, permissions)
3. **Intégrer** dans `./app.py` (odyssee-saas)
4. **Tester** que tout fonctionne correctement

## 🗂️ Organisation des fichiers

### odyssee-saas (répertoire actuel)
```
/
├── app.py                          # Application principale Flask
├── models.py                       # Modèles SQLAlchemy
├── config.py                       # Configuration
├── requirements.txt                # Dépendances Python
├── templates/
│   ├── base.html
│   ├── agency/                     # Templates pour les agences
│   └── super_admin/                # Templates pour le super admin
├── services/                       # Services métier
│   ├── email_sync/                # Synchronisation email
│   ├── analytics.py               # Analytics avancées
│   ├── reports.py                 # Génération de rapports
│   └── ...
└── migrations/                     # Migrations Alembic
```

## 📝 Exemples de migrations récentes

### Envoi d'offre par email
**Source** : Fonctionnalité imaginée/créée de zéro
**Résultat** : 
- Route `/api/trips/<int:trip_id>/send-offer` dans `app.py`
- Templates `offer_template.html` et `offer_template_down_payment.html`
- Modale dans `trip_detail.html`

### Autres fonctionnalités migrées
- Génération de voyages avec IA
- Publication FTP
- Paiements Stripe
- Notes internes
- CRM complet

## 🚀 Commandes utiles

```bash
# Lancer l'application
python app.py

# Migrations
flask db migrate -m "Description"
flask db upgrade

# Initialiser la DB
flask init-db
```

## 🔑 Points clés à retenir

1. **Toujours vérifier l'ancienne app** (`../App/app.py`) pour voir si une fonctionnalité existe déjà
2. **Adapter pour le multi-tenant** : ajouter les filtres par `agency_id`, vérifier les permissions
3. **Respecter l'architecture** : routes, services, templates, models
4. **Tester les permissions** : super_admin, agency_admin, seller
5. **Logger les activités** : utiliser `log_activity()` pour tracer les actions importantes

## 📊 Architecture de sécurité

### Décorateurs disponibles
- `@login_required` : Utilisateur connecté
- `@super_admin_required` : Super administrateur seulement
- `@agency_admin_required` : Admin d'agence
- `@agency_required` : Tout utilisateur d'agence (admin ou seller)

### Vérifications de sécurité
```python
# Vérifier l'appartenance à l'agence
if trip.agency_id != g.agency.id:
    abort(403)

# Vérifier les permissions vendeur
if g.user.role == 'seller' and trip.user_id != g.user.id:
    abort(403)
```

## 🎨 Stack technique

- **Backend** : Flask 3.x, SQLAlchemy, Flask-Migrate
- **Frontend** : Jinja2, TailwindCSS, JavaScript vanilla
- **Base de données** : SQLite (dev), PostgreSQL (prod recommandé)
- **Email** : Flask-Mail, Gmail/Outlook OAuth, SMTP/IMAP
- **Paiements** : Stripe
- **IA** : Google Gemini API
- **Médias** : Bannerbear, YouTube API

## 📌 Notes importantes

- Les clés API sont **chiffrées** en base de données (Google, Stripe, etc.)
- Utiliser `decrypt_api_key()` et `decrypt_config()` pour les récupérer
- Les quotas de génération sont gérés par utilisateur ET par agence
- Chaque agence a son propre sous-domaine

## 🔗 Liens utiles

- Documentation Flask : https://flask.palletsprojects.com/
- SQLAlchemy : https://www.sqlalchemy.org/
- Documentation Stripe : https://stripe.com/docs

---

**Dernière mise à jour** : 31 octobre 2025
**Auteur** : Équipe Odyssée SaaS
