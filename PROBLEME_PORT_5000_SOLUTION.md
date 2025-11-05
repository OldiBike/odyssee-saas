# 🚨 PROBLÈME IDENTIFIÉ : Conflit de Port avec AirPlay

## Le Problème

Le port **5000 est occupé par AirPlay** (ControlCenter d'Apple) sur Mac, ce qui empêche Flask de servir correctement les fichiers statiques, incluant le CSS du design system.

```bash
# Le serveur répond avec 403 Forbidden
curl -I http://localhost:5000/static/css/odyssee-design-system.css
# HTTP/1.1 403 Forbidden
# Server: AirTunes/860.7.1  ← C'est Apple, pas Flask!
```

## 🔧 Solution

### Étape 1 : Arrêter Flask actuel
Dans votre terminal où Flask tourne :
```bash
Ctrl+C
```

### Étape 2 : Relancer sur le port 5001
```bash
./run_dev.sh
```

OU manuellement :
```bash
flask run --port=5001
```

### Étape 3 : Accéder à l'application
```
http://localhost:5001
```

## ✅ Vérification

Après le redémarrage, le design system devrait être visible avec :
- Navigation glassmorphism
- Cards avec gradients
- Animations fluides
- Tous les styles modernes

## 🔄 Solution Alternative : Désactiver AirPlay Receiver

Si vous voulez garder le port 5000 :

1. **Préférences Système** → **Général** → **AirDrop et Handoff**
2. Décocher **"AirPlay Receiver"**
3. Redémarrer Flask

## 📝 Pour le Futur

Utilisez toujours le script `run_dev.sh` pour éviter ce problème :
```bash
./run_dev.sh
```

---

**Status** : Problème de port identifié et solution fournie  
**Date** : 02/11/2025
