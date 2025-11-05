# 📦 Guide d'import des données vers Railway

Ce guide explique comment transférer vos données locales vers votre déploiement Railway.

## 🎯 Prérequis

- Le fichier SQL exporté : `db_export_YYYYMMDD_HHMMSS.sql`
- Accès à Railway CLI ou au dashboard Railway

## 📋 Méthode 1 : Via Railway CLI (Recommandée)

### Étape 1 : Installer Railway CLI

```bash
# macOS / Linux
curl -fsSL https://railway.app/install.sh | sh

# Vérifier l'installation
railway --version
```

### Étape 2 : Se connecter

```bash
railway login
```

### Étape 3 : Lier votre projet

```bash
# Dans le dossier du projet
railway link
```

### Étape 4 : Uploader le fichier SQL

```bash
# Copier le fichier dans l'environnement Railway
railway run bash
# Puis dans le shell Railway :
exit
```

### Étape 5 : Exécuter l'import

```bash
railway run flask import-data db_export_YYYYMMDD_HHMMSS.sql
```

## 📋 Méthode 2 : Via Dashboard Railway + Variables d'environnement

### Étape 1 : Préparer le fichier

1. Hébergez temporairement votre fichier SQL sur un service comme :
   - GitHub Gist (privé)
   - Dropbox
   - Google Drive (lien de partage)

### Étape 2 : Créer un script d'import automatique

Créez un fichier `import_from_url.py` :

```python
import requests
import os

# URL de votre fichier SQL
SQL_URL = os.getenv('SQL_IMPORT_URL')

if SQL_URL:
    print("📥 Téléchargement du fichier SQL...")
    response = requests.get(SQL_URL)
    
    with open('import_temp.sql', 'wb') as f:
        f.write(response.content)
    
    print("✅ Fichier téléchargé")
    print("📊 Lancement de l'import...")
    
    os.system('flask import-data import_temp.sql')
    
    # Nettoyer
    os.remove('import_temp.sql')
    print("✅ Import terminé")
else:
    print("❌ Variable SQL_IMPORT_URL non définie")
```

### Étape 3 : Sur Railway

1. Ajoutez la variable d'environnement :
   - `SQL_IMPORT_URL` = URL de votre fichier SQL

2. Lancez une commande one-shot :
   ```bash
   python import_from_url.py
   ```

## 📋 Méthode 3 : Import manuel par étapes

### Si le fichier est trop gros (>10Mo)

1. **Splitter le fichier SQL** :

```bash
# Sur votre machine locale
split -l 10000 db_export_YYYYMMDD_HHMMSS.sql db_part_
```

2. **Importer partie par partie** sur Railway :

```bash
railway run flask import-data db_part_aa
railway run flask import-data db_part_ab
# etc...
```

## 🔍 Vérification après import

### Via Railway CLI

```bash
railway run flask shell

# Dans le shell Flask
>>> from models import Trip, Client, Agency
>>> print(f"Voyages: {Trip.query.count()}")
>>> print(f"Clients: {Client.query.count()}")
>>> print(f"Agences: {Agency.query.count()}")
>>> exit()
```

### Via l'interface web

1. Connectez-vous à votre app Railway
2. Allez sur le dashboard
3. Vérifiez que vos données sont bien présentes

## ⚠️ Important

- **Sauvegarde** : Railway fait des sauvegardes automatiques, mais gardez votre fichier SQL local
- **Permissions** : Assurez-vous que votre base Railway est en lecture/écriture
- **Variables d'env** : Vérifiez que `DATABASE_URL` ou `SQLALCHEMY_DATABASE_URI` est bien configuré

## 🔄 Migration après import

Si vous avez fait des changements de structure après l'export :

```bash
railway run flask db upgrade
```

## 🆘 En cas de problème

### Erreur "Foreign key constraint"

Le script gère automatiquement les contraintes, mais si vous avez une erreur :

```bash
# Désactiver temporairement les contraintes
railway run flask shell
>>> from app import db
>>> db.engine.execute("PRAGMA foreign_keys=OFF")
>>> exit()

# Puis réessayer l'import
railway run flask import-data db_export_YYYYMMDD_HHMMSS.sql
```

### Erreur "File not found"

Assurez-vous que le fichier est bien dans le répertoire courant :

```bash
railway run ls -la
```

## 📊 Export régulier (optionnel)

Pour automatiser les exports, ajoutez un cron job :

```python
# Dans app.py, ajouter une route protégée
@app.route('/admin/backup')
@super_admin_required
def backup_database():
    import subprocess
    subprocess.run(['python', 'export_db.py'])
    # Puis uploader le fichier vers votre stockage cloud
    return "Backup lancé"
```

## 🎉 Résultat

Une fois l'import terminé, toutes vos données locales seront disponibles sur Railway :
- ✅ Voyages
- ✅ Clients
- ✅ Agences
- ✅ Utilisateurs
- ✅ Configurations

---

**Note** : Ce processus est sécurisé car :
- Les mots de passe restent hashés
- Les clés API restent chiffrées
- Les tokens ne sont jamais exposés
