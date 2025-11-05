# 🔧 Guide de Débogage - Design System

## Problème : Le design ne change pas après rechargement

### Solutions à tester dans l'ordre :

## 1. Redémarrer le Serveur Flask ⚠️ IMPORTANT
```bash
# Arrêter le serveur (Ctrl+C dans le terminal)
# Puis relancer :
python app.py
# ou
flask run
```

**⚡ Flask met en cache les templates. Un redémarrage est OBLIGATOIRE pour voir les changements.**

---

## 2. Vider le Cache du Navigateur

### Option A : Force Refresh (Recommandé)
- **Mac** : `Cmd + Shift + R`
- **Windows/Linux** : `Ctrl + Shift + R` ou `Ctrl + F5`

### Option B : Ouvrir en Navigation Privée
- **Mac** : `Cmd + Shift + N`
- **Windows/Linux** : `Ctrl + Shift + N`

### Option C : Vider complètement le cache
1. Ouvrir les DevTools (F12)
2. Aller dans l'onglet "Network"
3. Clic droit sur "Disable cache" (décocher puis recocher)
4. Rafraîchir la page

---

## 3. Vérifier que le CSS est bien chargé

### Dans le navigateur :
1. Ouvrir les DevTools (F12)
2. Aller dans l'onglet "Network"
3. Rafraîchir la page
4. Chercher `odyssee-design-system.css`
5. Vérifier :
   - ✅ Status : 200 (OK)
   - ❌ Status : 404 (fichier non trouvé)
   - ⚠️ Status : 304 (cache - faire force refresh)

---

## 4. Vérifier le code source de la page

1. Clic droit sur la page → "Afficher le code source"
2. Chercher `odyssee-design-system.css`
3. Le lien devrait ressembler à :
```html
<link rel="stylesheet" href="/static/css/odyssee-design-system.css">
```

Si le lien n'apparaît pas, le template `base.html` n'a pas été pris en compte.
→ **Solution : Redémarrer le serveur Flask**

---

## 5. Tester l'URL du CSS directement

Dans le navigateur, aller sur :
```
http://localhost:5000/static/css/odyssee-design-system.css
```
(Adapter le port si nécessaire)

- ✅ Si le CSS s'affiche : Le fichier est accessible
- ❌ Si erreur 404 : Problème de configuration Flask

---

## 6. Configuration Flask (si problème persiste)

Vérifier dans `app.py` ou `config.py` :

```python
# La configuration des fichiers statiques devrait être :
app = Flask(__name__, static_folder='static')

# Ou si vous utilisez un blueprint :
app.static_folder = 'static'
app.static_url_path = '/static'
```

---

## 🎯 Checklist Rapide

Avant de considérer qu'il y a un bug :

- [ ] ✅ J'ai **redémarré le serveur Flask**
- [ ] ✅ J'ai fait un **Force Refresh** (Cmd+Shift+R / Ctrl+Shift+R)
- [ ] ✅ J'ai testé en **navigation privée**
- [ ] ✅ Le fichier CSS apparaît dans les DevTools → Network
- [ ] ✅ Le lien CSS apparaît dans le code source HTML

---

## 🔍 Vérification Visuelle Attendue

Après le rechargement avec le design system, vous devriez voir :

### Navigation
- Effet glassmorphism (transparent avec flou)
- Boutons avec gradients bleu/violet au survol
- Avatar rond avec gradient

### Dashboard
- Cards des statistiques avec gradients de couleur
- Animations d'entrée séquentielles
- Barres de progression avec gradients
- Hover effects sur les cards

### Si vous ne voyez RIEN de cela
→ Le CSS n'est **PAS chargé** → Redémarrer Flask !

---

## 🐛 Debug Avancé

### Ajouter une version au CSS pour forcer le reload
Dans `base.html`, modifier temporairement :
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/odyssee-design-system.css') }}?v=2">
```

Le `?v=2` force le navigateur à recharger le fichier.

### Vérifier les permissions du fichier
```bash
ls -l static/css/odyssee-design-system.css
```
Le fichier doit être lisible (r--) pour tous.

---

## 📞 Contact Support

Si après toutes ces étapes le problème persiste :

1. Fournir une capture d'écran de la console (F12)
2. Fournir le Network tab (F12) avec le CSS
3. Indiquer la version de Flask : `flask --version`
4. Indiquer le navigateur utilisé

---

**Mise à jour** : 02/11/2025
