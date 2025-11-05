# 🗄️ Configuration PostgreSQL sur Railway

## 🎯 Problème actuel

Railway a un système de fichiers **éphémère** - tous les fichiers (dont la DB SQLite) sont perdus à chaque redéploiement. C'est pourquoi vos données ne persistent pas.

## ✅ Solution : Utiliser PostgreSQL

Vous avez déjà un service PostgreSQL dans votre projet, il faut juste le lier à `odyssee-saas`.

## 📋 Étapes (5 minutes)

### 1. Aller sur le Dashboard Railway

1. Ouvrez votre navigateur
2. Allez sur : https://railway.app/project/45ef61a3-5cc1-44a2-8d5c-f09af8d6ec92
3. Connectez-vous si nécessaire

### 2. Lier PostgreSQL au service odyssee-saas

#### Option A : Via "Reference Variables" (Recommandé)

1. Dans votre projet, cliquez sur le service **`Postgres`**
2. Allez dans l'onglet **"Variables"**
3. Vous devriez voir : `DATABASE_URL`, `PGDATABASE`, `PGHOST`, etc.
4. Retournez à la vue du projet (cliquez sur le nom du projet en haut)
5. Cliquez sur le service **`odyssee-saas`**
6. Allez dans l'onglet **"Variables"**
7. Cliquez sur **"+ New Variable"**
8. Choisissez **"Add Reference"**
9. Sélectionnez :
   - Service: **Postgres**
   - Variable: **DATABASE_URL**
10. Cliquez sur **"Add"**

#### Option B : Via les Paramètres (Alternative)

1. Cliquez sur le service **`odyssee-saas`**
2. Allez dans **"Settings"**
3. Cherchez la section **"Service Variables"** ou **"Connected Services"**
4. Ajoutez une connexion vers le service **Postgres**
5. Cela créera automatiquement `DATABASE_URL`

### 3. Redéployer

Une fois `DATABASE_URL` ajouté, Railway redéploiera automatiquement.

Sinon, déclenchez manuellement :
1. Allez dans l'onglet **"Deployments"** du service `odyssee-saas`
2. Cliquez sur **"Redeploy"**

### 4. Vérifier la variable

Depuis votre terminal local :

```bash
railway variables
```

Vous devriez maintenant voir `DATABASE_URL` dans la liste.

## 🚀 Une fois configuré

### Étape A : Créer les tables PostgreSQL

```bash
railway run flask db upgrade
```

### Étape B : Importer vos données

```bash
railway run flask import-data db_export_20251105_155500.sql
```

### Étape C : Vérifier

```bash
railway run python verify_import.py
```

Vous devriez voir :
```
✅ Agences      : 2
✅ Voyages      : 4
✅ Utilisateurs : 3
✅ Clients      : 1
```

## 🎉 Résultat

Une fois fait :
- ✅ Les données persisteront entre les déploiements
- ✅ PostgreSQL est plus performant que SQLite
- ✅ Vous pourrez continuer à développer normalement

## 📝 Note importante

**En local**, l'app continuera à utiliser SQLite (`instance/odyssee.db`).  
**Sur Railway**, l'app utilisera automatiquement PostgreSQL via `DATABASE_URL`.

Le `config.py` détecte automatiquement l'environnement et choisit la bonne base de données.

## 🔄 Workflow après configuration

```bash
# En local : développer avec SQLite
flask run

# Push vers GitHub
git push origin main

# Railway redéploie automatiquement avec PostgreSQL
# Les données PostgreSQL restent intactes
```

## 🆘 Besoin d'aide ?

Si vous avez du mal à trouver où lier les services dans le dashboard, voici l'URL directe de votre projet :

**Projet :** https://railway.app/project/45ef61a3-5cc1-44a2-8d5c-f09af8d6ec92

1. Cliquez sur **Postgres** (voir DATABASE_URL)
2. Retour au projet
3. Cliquez sur **odyssee-saas**
4. Variables → **+ New Variable** → **Add Reference** → Postgres → DATABASE_URL

---

Une fois fait, faites-moi signe et je lancerai les commandes pour créer les tables et importer les données ! 🚀
