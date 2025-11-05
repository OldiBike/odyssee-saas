# Documentation : Système de Publication Multi-Protocoles

## Vue d'ensemble

Le système de publication d'Odyssée a été amélioré pour supporter plusieurs protocoles de transfert de fichiers, permettant aux agences de publier leurs fiches de voyage sur différents types d'hébergeurs.

## Protocoles Supportés

### 1. FTP (File Transfer Protocol)
- **Port par défaut** : 21
- **Sécurité** : ❌ Non sécurisé (données en clair)
- **Usage recommandé** : Hébergeurs anciens uniquement
- **Avantages** : Compatible avec tous les hébergeurs
- **Inconvénients** : Aucun chiffrement des données

### 2. FTPS (FTP over TLS/SSL)
- **Port par défaut** : 990
- **Sécurité** : ✅ Sécurisé (chiffrement TLS/SSL)
- **Usage recommandé** : Hébergeurs modernes supportant le chiffrement
- **Avantages** : Compatible avec la plupart des hébergeurs FTP, sécurisé
- **Inconvénients** : Peut nécessiter une configuration firewall

### 3. SFTP (SSH File Transfer Protocol)
- **Port par défaut** : 22
- **Sécurité** : ✅ Très sécurisé (chiffrement SSH)
- **Usage recommandé** : Serveurs dédiés, VPS, hébergeurs modernes
- **Avantages** : Très sécurisé, authentification robuste
- **Inconvénients** : Nécessite la bibliothèque `paramiko`

### 4. API HTTP/HTTPS (Contournement)
- **Port par défaut** : 443 (HTTPS) ou 80 (HTTP)
- **Sécurité** : ✅ Sécurisé si HTTPS avec authentification Bearer
- **Usage recommandé** : **Hostinger depuis Railway** et autres hébergeurs bloquant les connexions cloud
- **Avantages** : Contourne les blocages d'IP, flexible, peut être déployé n'importe où
- **Inconvénients** : Nécessite de créer/héberger une API intermédiaire personnalisée

> **⚠️ Cas d'usage critique : Hostinger depuis Railway**
>
> Hostinger (et d'autres hébergeurs mutualisés) bloque les connexions FTP/SFTP provenant d'adresses IP de plateformes cloud comme Railway, Heroku, etc. Pour contourner ce problème, vous devez :
> 1. Créer une API intermédiaire hébergée ailleurs (ex: sur le serveur final)
> 2. Configurer Odyssée pour utiliser le protocole `api`
> 3. L'API intermédiaire reçoit le HTML et le publie localement via FTP

## Configuration dans l'Interface Admin

### Champs de Configuration

1. **Protocole** : Sélection du type de connexion
   - `auto` : Détection automatique basée sur le port
   - `ftp` : FTP standard (non sécurisé)
   - `ftps` : FTP sécurisé (TLS/SSL)
   - `sftp` : SFTP (SSH)

2. **Port** : Port de connexion
   - Laissez vide pour utiliser le port par défaut
   - Exemples : 21 (FTP), 990 (FTPS), 22 (SFTP)

3. **Hôte** : Adresse du serveur
   - Exemple : `ftp.example.com`

4. **Chemin** : Répertoire de destination sur le serveur
   - Exemple : `/public_html/voyages/`
   - Les répertoires manquants seront créés automatiquement

5. **Utilisateur** : Nom d'utilisateur pour la connexion

6. **Mot de passe** : Mot de passe (chiffré en base de données)

## Détection Automatique du Protocole

Lorsque le mode `auto` est sélectionné, le système détecte automatiquement le protocole à utiliser :

```
Port 22  → SFTP
Port 990 → FTPS  
Autre    → FTP
```

## Fonctionnalités Avancées

### Création Automatique de Répertoires

Le système crée automatiquement les répertoires manquants sur le serveur distant, évitant les erreurs de publication.

### Gestion des Erreurs

Chaque tentative de publication génère des logs détaillés :
- ✅ Succès : Confirmation de la publication
- ❌ Erreur : Message d'erreur détaillé pour le débogage

### Timeout & Résilience

- **Timeout de connexion** : 30 secondes
- **Gestion des déconnexions** : Fermeture propre des connexions
- **Nettoyage** : Suppression automatique des fichiers temporaires

## Configuration Technique

### Structure du fichier `services/publication.py`

```python
def publish_via_ftp(html_content, filename, ftp_config):
    """
    Point d'entrée principal pour la publication.
    Route automatiquement vers le bon protocole.
    """
    protocol = ftp_config.get('protocol', 'auto')
    
    # Détection automatique ou routage manuel
    if protocol == 'sftp':
        return _publish_sftp(...)
    elif protocol == 'ftps':
        return _publish_ftps(...)
    else:
        return _publish_ftp(...)
```

### Dépendances

```txt
paramiko==3.4.0  # Pour SFTP
```

## Exemples de Configuration par Hébergeur

### OVH
```
Protocole: SFTP
Port: 22
Hôte: ssh.cluster0XX.hosting.ovh.net
Chemin: /www/voyages/
```

### 1&1 IONOS
```
Protocole: FTPS
Port: 990
Hôte: home123456789.1and1-data.host
Chemin: /voyages/
```

### Hostinger
```
Protocole: FTP ou FTPS
Port: 21 ou 990
Hôte: ftp.hostinger.com
Chemin: /public_html/voyages/
```

### DigitalOcean / Serveur Dédié
```
Protocole: SFTP
Port: 22
Hôte: votre-ip-serveur
Chemin: /var/www/html/voyages/
```

## Migration depuis l'Ancien Système

Les agences utilisant déjà le système FTP n'ont rien à faire. Le système reste rétrocompatible :
- Les anciennes configurations FTP continuent de fonctionner
- Il suffit d'ajouter le protocole et le port pour utiliser FTPS ou SFTP

## Dépannage

### Erreur : "Paramiko n'est pas installé"
```bash
pip install paramiko==3.4.0
```

### Erreur : "Connection timeout"
- Vérifier que le port est correct
- Vérifier que le firewall autorise les connexions sortantes

### Erreur : "Authentication failed"
- Vérifier les identifiants
- Pour SFTP : vérifier que l'authentification par mot de passe est activée

### Erreur : "Permission denied"
- Vérifier les permissions du répertoire distant
- S'assurer que l'utilisateur a les droits d'écriture

## Sécurité

### Chiffrement des Credentials
- Tous les mots de passe sont chiffrés en base de données
- Utilisation de `cryptography.fernet` pour le chiffrement

### Bonnes Pratiques
1. ✅ Préférer SFTP ou FTPS plutôt que FTP
2. ✅ Utiliser des mots de passe forts
3. ✅ Limiter les permissions de l'utilisateur FTP/SFTP
4. ✅ Utiliser des répertoires dédiés avec permissions restrictives

## API Backend

La configuration est envoyée depuis le frontend via :

```javascript
const ftpConfig = {
    host: "ftp.example.com",
    path: "/public_html/voyages/",
    user: "username",
    password: "password",
    protocol: "sftp",  // 'ftp', 'ftps', 'sftp', 'auto'
    port: "22"
};
```

## Tests de Connexion

Pour tester la configuration, créez un voyage de test et utilisez la fonction "Publier" dans l'interface. Les logs du serveur indiqueront si la connexion a réussi.

---

**Date de dernière mise à jour** : 30 octobre 2025  
**Version** : 2.0
