# 🔄 Workflow de Développement Odyssée

## 📋 Vue d'ensemble

Ce document explique comment développer en local et déployer sur Railway.

---

## 🏠 Développement Local (Recommandé)

### Démarrage rapide

```bash
./run_dev.sh
```

**Caractéristiques :**
- ✅ Base de données **SQLite** locale (`instance/odyssee.db`)
- ✅ Rapide et simple
- ✅ Pas de connexion réseau requise
- ✅ Idéal pour développer et tester

**Accès:** http://localhost:5001

---

## 🚂 Développement avec Railway (Optionnel)

### Quand l'utiliser ?

Utilisez cette méthode uniquement si vous devez :
- Tester avec les données de production
- Vérifier une migration de base de données
- Débugger un problème spécifique à PostgreSQL

### Commande

```bash
./run_dev_railway.sh
```

**⚠️ ATTENTION :**
- Utilise la base de données **PostgreSQL de PRODUCTION**
- Toute modification affecte la production
- À utiliser avec précaution

---

## 🚀 Déploiement sur Railway

### Processus automatique

Railway est configuré pour déployer automatiquement à chaque push sur `main`.

### Étapes

1. **Commitez vos changements**
```bash
git add .
git commit -m "Description de vos modifications"
```

2. **Poussez vers GitHub**
```bash
git push origin main
```

3. **Railway déploie automatiquement** ⚡
   - Build de l'application
   - Exécution des migrations
   - Redémarrage du service
   - Environ 2-3 minutes

### Vérification du déploiement

```bash
# Voir les logs en temps réel
railway logs

# Vérifier le statut
railway status
```

**URL de production :** https://odyssee-saas-production.up.railway.app

---

## 🗄️ Gestion de la Base de Données

### En local (SQLite)

- Fichier : `instance/odyssee.db`
- Automatiquement créé au premier lancement
- Données isolées de la production

### En production (PostgreSQL Railway)

- Hébergé sur Railway
- Sauvegardé automatiquement
- Accessible via `railway run` si nécessaire

### Migrations

```bash
# Créer une nouvelle migration
flask db migrate -m "Description"

# Appliquer les migrations en local
flask db upgrade

# Les migrations sont appliquées automatiquement sur Railway au déploiement
```

---

## 🔧 Commandes Utiles

### Railway CLI

```bash
# Voir les variables d'environnement
railway variables

# Ouvrir le dashboard Railway dans le navigateur
railway open

# Voir les logs
railway logs --follow

# Exécuter une commande avec l'environnement Railway
railway run <commande>
```

### Flask

```bash
# Shell interactif avec contexte app
flask shell

# Créer un super admin
python create_agency.py
```

### Git

```bash
# Voir l'état des fichiers
git status

# Voir l'historique
git log --oneline

# Annuler le dernier commit (garde les modifications)
git reset --soft HEAD~1
```

---

## 📁 Structure du Projet

```
Odyssee/
├── app.py                    # Point d'entrée principal
├── config.py                 # Configuration
├── models.py                 # Modèles de base de données
├── run_dev.sh               # 🟢 Démarrage local (SQLite)
├── run_dev_railway.sh       # 🔴 Démarrage avec Railway (PostgreSQL prod)
├── start.sh                 # Script de démarrage Railway
├── requirements.txt         # Dépendances Python
├── Procfile                 # Configuration Railway
├── nixpacks.toml           # Configuration build Railway
├── .env                     # Variables d'environnement locales (à ne PAS commit)
├── .gitignore              # Fichiers ignorés par Git
│
├── migrations/              # Migrations de base de données
├── services/               # Services métier
├── templates/              # Templates HTML
├── static/                 # CSS, JS, images
└── instance/               # Base SQLite locale (ignoré par Git)
```

---

## 🔐 Variables d'Environnement

### Local (.env)

Fichier `.env` pour le développement local.
**Ne jamais commiter ce fichier !**

### Production (Railway)

Variables configurées dans le dashboard Railway.
Injectées automatiquement au runtime.

Variables importantes :
- `DATABASE_URL` - URL PostgreSQL (générée par Railway)
- `SECRET_KEY` - Clé secrète Flask
- `MASTER_ENCRYPTION_KEY` - Clé de chiffrement

---

## ❓ Résolution de Problèmes

### L'app ne démarre pas localement

```bash
# Vérifier les dépendances
pip install -r requirements.txt

# Vérifier que le port 5001 est libre
lsof -i:5001

# Tuer le processus si nécessaire
lsof -ti:5001 | xargs kill -9
```

### Erreur de migration

```bash
# Supprimer la base locale et recréer
rm instance/odyssee.db
flask db upgrade
```

### Railway ne déploie pas

```bash
# Vérifier les logs
railway logs

# Vérifier le status
railway status

# Forcer un redéploiement
git commit --allow-empty -m "Force redeploy"
git push origin main
```

---

## 📝 Checklist Avant Push

- [ ] Tests locaux réussis
- [ ] Pas de données sensibles dans le code
- [ ] Fichier `.env` non commité
- [ ] Migrations créées si modèle modifié
- [ ] Code commenté si nécessaire
- [ ] Message de commit descriptif

---

## 🎯 Best Practices

1. **Développez toujours en local** avec `./run_dev.sh`
2. **Committez régulièrement** avec des messages clairs
3. **Testez avant de pusher** sur GitHub
4. **Évitez de modifier directement** la base PostgreSQL de prod
5. **Utilisez des migrations** pour tout changement de schéma
6. **Gardez le .env à jour** mais ne le commitez jamais

---

## 🆘 Support

En cas de problème :

1. Consultez les logs : `railway logs`
2. Vérifiez la documentation : `/README.md`
3. Contactez l'équipe technique

---

**🎉 Happy Coding !**
