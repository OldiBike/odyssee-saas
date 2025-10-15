# 🚀 Odyssée SaaS - Plateforme Multi-Agences de Voyages

Application Flask SaaS pour la gestion de voyages par plusieurs agences de tourisme.

## 📋 Compatibilité Python

### ⚠️ Version Recommandée : Python 3.11.9

**Important** : Cette application a été testée et est compatible avec **Python 3.11.x**. 

Python 3.13 est trop récent et certaines dépendances (notamment `psycopg2-binary`, `lxml`, `pydantic-core`) ont des problèmes de compilation avec cette version.

### Installation de Python 3.11 (Recommandé)

#### Avec pyenv (MacOS/Linux)
```bash
# Installer pyenv si nécessaire
brew install pyenv  # MacOS
# ou suivez https://github.com/pyenv/pyenv#installation

# Installer Python 3.11.9
pyenv install 3.11.9

# Définir Python 3.11.9 pour ce projet
pyenv local 3.11.9

# Vérifier la version
python --version  # Devrait afficher Python 3.11.9
```

#### Avec Homebrew (MacOS)
```bash
brew install python@3.11
```

#### Téléchargement direct
Téléchargez Python 3.11 depuis [python.org](https://www.python.org/downloads/)

---

## 🛠️ Installation

### 1. Cloner le projet
```bash
git clone https://github.com/votre-repo/odyssee-saas.git
cd odyssee-saas
```

### 2. Créer un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

### 3. Installer les dépendances
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Si vous avez des erreurs de compilation :
- Vérifiez que vous utilisez Python 3.11.x : `python --version`
- Sur MacOS, installez les outils de développement : `xcode-select --install`
- Essayez d'installer les packages problématiques en binary wheel : `pip install --only-binary :all: psycopg2-binary lxml`

### 4. Configuration
```bash
# Copier le fichier d'environnement
cp .env.example .env

# Éditer .env et remplir vos clés
nano .env  # ou votre éditeur préféré
```

**Variables minimales à configurer** :
```bash
SECRET_KEY=votre-cle-secrete-unique
MASTER_ENCRYPTION_KEY=votre-cle-chiffrement-unique
```

**Générer des clés sécurisées** :
```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# MASTER_ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 5. Initialiser la base de données
```bash
flask init-db
```

Cela va créer :
- ✅ Les tables de la base de données
- ✅ Le compte super-admin (credentials dans votre `.env`)

### 6. Lancer l'application
```bash
flask run
```

L'application sera accessible sur : http://localhost:5000

---

## 📦 Structure du Projet

```
odyssee-saas/
├── app.py                  # Application Flask principale
├── config.py              # Configuration
├── models.py              # Modèles de données SQLAlchemy
├── schemas.py             # Schémas de validation Pydantic
├── requirements.txt       # Dépendances Python
├── .python-version       # Version Python recommandée
├── .env                   # Variables d'environnement (à créer)
├── .env.example          # Template des variables
│
├── migrations/           # Migrations Alembic
├── instance/             # Base de données SQLite (dev)
├── templates/            # Templates Jinja2
│   ├── agency/          # Templates agence
│   ├── super_admin/     # Templates super-admin
│   └── ...
├── static/              # CSS, JS, images
├── services/            # Services métier
│   ├── ai_assistant.py
│   ├── api_gatherer.py
│   ├── template_engine.py
│   ├── mailer.py
│   ├── payment.py
│   └── publication.py
└── utils/               # Utilitaires
    └── crypto.py        # Chiffrement
```

---

## 🔐 Sécurité

### Clés de Chiffrement

**CRITIQUE** : La `MASTER_ENCRYPTION_KEY` ne doit **JAMAIS** être changée en production, sinon toutes les données chiffrées (clés API des agences) seront perdues.

### Données Sensibles Chiffrées

Les données suivantes sont chiffrées en base de données :
- Clés API Google (par agence)
- Clés API Stripe (par agence)
- Configurations email (par agence)
- Configurations FTP/SFTP (par agence)

---

## 🎯 Fonctionnalités

### Multi-Tenant
- Chaque agence a son propre sous-domaine
- Isolation complète des données
- Configuration personnalisée par agence

### Rôles Utilisateurs
- **Super Admin** : Gestion de toute la plateforme
- **Agency Admin** : Gestion d'une agence
- **Seller** : Création et gestion de voyages

### Génération de Voyages
- Wizard IA avec Gemini AI
- Formulaire manuel complet
- Intégration Google Places API
- Génération automatique de programmes

### Gestion Clients & Voyages
- CRUD complet clients
- États des voyages (proposé, assigné, vendu)
- Génération de fiches PDF
- Publication via FTP/SFTP

### Paiements
- Intégration Stripe pour acomptes
- Gestion paiements manuels
- Génération de factures

---

## 🚀 Déploiement en Production

### Railway (Recommandé)

1. **Créer un nouveau projet sur [Railway](https://railway.app)**

2. **Connecter votre repo GitHub**

3. **Ajouter PostgreSQL** :
   - Railway configure automatiquement `DATABASE_URL`

4. **Définir les variables d'environnement** :
   ```
   FLASK_ENV=production
   SECRET_KEY=<votre-clé-générée>
   MASTER_ENCRYPTION_KEY=<votre-clé-générée>
   SUPER_ADMIN_USERNAME=admin
   SUPER_ADMIN_PASSWORD=<mot-de-passe-fort>
   SUPER_ADMIN_EMAIL=admin@votre-domaine.com
   ```

5. **Ajouter Redis (optionnel mais recommandé)** :
   - Ajouter le service Redis
   - Railway configurera automatiquement `REDIS_URL`
   - Définir `SESSION_TYPE=redis`

6. **Initialiser la base de données** :
   ```bash
   railway run flask init-db
   ```

### Configuration DNS

Pour utiliser des sous-domaines par agence :
```
*.votre-domaine.com → IP de votre serveur
```

---

## 🧪 Tests

```bash
# TODO: Ajouter des tests unitaires
pytest
```

---

## 📚 APIs Externes Utilisées

### Google APIs (optionnel)
- **Places API** : Autocomplete hôtels et lieux
- **Gemini AI** : Parsing de prompts en langage naturel
- **YouTube Data API** : Vidéos de destinations

### Stripe (optionnel)
- Génération de liens de paiement pour acomptes

---

## 🐛 Dépannage

### Erreur : "No changes in schema detected"
C'est normal si votre modèle et votre BDD sont déjà synchronisés.

### Erreur de compilation des packages
Vérifiez votre version Python : `python --version`
- ✅ Python 3.11.x : Compatible
- ⚠️ Python 3.13.x : Problèmes de compilation

### Erreur : "Le gestionnaire de chiffrement n'a pas été initialisé"
Vérifiez que `MASTER_ENCRYPTION_KEY` est défini dans `.env`

---

## 📄 Licence

Propriétaire - Tous droits réservés

---

## 👥 Support

Pour toute question ou problème :
- Ouvrir une issue sur GitHub
- Contacter l'équipe de développement

---

## 🔄 Mises à Jour

### Version 1.0.0 (Actuelle)
- ✅ Architecture multi-tenant
- ✅ Génération de voyages avec IA
- ✅ Gestion complète des clients
- ✅ Intégration Stripe
- ✅ Publication FTP/SFTP
- ✅ Rate limiting et sécurité
- ✅ Validation des données avec Pydantic

---

**Bon développement ! 🎉**
