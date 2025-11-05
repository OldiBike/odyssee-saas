# 🐛 DEBUG - Synchronisation IMAP Manuelle

## 📋 CONTEXTE

Configuration SMTP/IMAP manuelle mise en place pour Hostinger. La synchronisation échoue avec plusieurs erreurs.

## ❌ ERREURS OBSERVÉES

### 1. Clé API Gemini manquante
```
Aucune clé API Gemini fournie
```
➡️ Le service AI Summarizer ne trouve pas la clé Gemini

### 2. Erreur NoneType lors du traitement
```
Erreur lors du traitement de 1: 'NoneType' object has no attribute 'lower'
Erreur lors du traitement de 2: 'NoneType' object has no attribute 'lower'
... (x16 messages)
```
➡️ Un champ None essaie d'appeler `.lower()` quelque part

### 3. KeyError dans app.py
```python
KeyError: 'processed'
File "app.py", line 2835, in trigger_email_sync
    details=f"Synchronisation: {stats['processed']} emails traités, {stats['saved']} sauvegardés"
```
➡️ La méthode `sync_emails()` ne retourne pas le bon format de dictionnaire

## 🔍 CODE CONCERNÉ

### app.py:2821-2845 (route trigger_email_sync)
```python
@app.route('/api/email-sync/trigger', methods=['POST'])
@agency_admin_required
@limiter.limit("5 per hour")
def trigger_email_sync():
    """Lance une synchronisation manuelle des emails"""
    from services.email_sync.email_sync_manager import EmailSyncManager
    
    if not g.agency.email_sync_enabled:
        return jsonify({
            'success': False,
            'error': 'La synchronisation email n\'est pas activée'
        }), 400
    
    try:
        # Initialiser le gestionnaire de sync
        manager = EmailSyncManager(g.agency)  # ✅ CORRIGÉ
        
        # Lancer la synchronisation
        stats = manager.sync_emails()  # ⚠️ RETOURNE QUOI ?
        
        # Mettre à jour la date de dernière sync
        g.agency.email_last_sync_at = datetime.utcnow()
        db.session.commit()
        
        # Log de l'activité
        log_activity(
            action='email_sync_triggered',
            user_id=g.user.id,
            agency_id=g.agency.id,
            details=f"Synchronisation: {stats['processed']} emails traités, {stats['saved']} sauvegardés"
            # ⚠️ KeyError ici car stats n'a pas ces clés
        )
```

### services/email_sync/email_sync_manager.py
Le fichier `EmailSyncManager` a été modifié pour supporter le provider 'manual' mais :
1. Vérifie que `sync_emails()` retourne bien un dict avec les clés `'processed'` et `'saved'`
2. Vérifie que l'initialisation avec `agency` (objet) fonctionne

### services/email_sync/imap_sync.py
Service créé pour IMAP. Vérifie :
1. Que `get_new_messages()` fonctionne correctement
2. Que `get_message_details()` retourne les bons champs
3. Qu'il n'y a pas de champs None qui causent l'erreur `.lower()`

### services/email_sync/email_parser.py
Probablement la source de l'erreur `'NoneType' object has no attribute 'lower'`. 
Chercher où `.lower()` est appelé sur un champ qui peut être None.

### services/email_sync/ai_summarizer.py
L'erreur "Aucune clé API Gemini fournie" vient d'ici.
Vérifier comment la clé Gemini est récupérée.

## 🎯 ACTIONS À FAIRE

### 1. Corriger EmailSyncManager.sync_emails()
Assurer qu'il retourne :
```python
{
    'processed': int,  # Nombre d'emails traités
    'saved': int       # Nombre d'emails sauvegardés
}
```

### 2. Corriger l'erreur NoneType
Dans `email_parser.py`, chercher où `.lower()` est appelé et ajouter une vérification :
```python
# Avant
if subject.lower() in ['urgent', ...]:

# Après
if subject and subject.lower() in ['urgent', ...]:
```

### 3. Corriger la clé Gemini
Dans `ai_summarizer.py`, vérifier comment récupérer la clé depuis l'agence :
```python
# Possible fix
from utils.crypto import decrypt_api_key

gemini_key = decrypt_api_key(agency.google_api_key_encrypted) if agency.google_api_key_encrypted else None
```

## 📁 FICHIERS À VÉRIFIER EN PRIORITÉ

1. **services/email_sync/email_sync_manager.py** - Méthode `sync_emails()`
2. **services/email_sync/email_parser.py** - Chercher `.lower()` sur champs optionnels
3. **services/email_sync/ai_summarizer.py** - Récupération clé Gemini
4. **services/email_sync/imap_sync.py** - Format des données retournées

## 🔧 CONFIGURATION BDD

Les colonnes suivantes ont été ajoutées à `Agency` :
- `smtp_config_encrypted` (Text)
- `imap_config_encrypted` (Text)
- `email_config_type` (String 20) - 'oauth' ou 'manual'
- `email_sync_provider` (String 50) - 'gmail', 'outlook', ou 'manual'
- `email_sync_email` (String 255) - Email configuré

## 📝 NOTES

- La configuration SMTP fonctionne (test de connexion OK)
- L'interface web est complète
- Le service IMAPSyncService a été créé
- Le problème est dans la logique de synchronisation et le traitement des emails

## 🎯 OBJECTIF FINAL

Que la synchronisation IMAP fonctionne :
1. Récupération des emails via IMAP ✅ (service créé)
2. Parsing des emails ⚠️ (erreur NoneType)
3. Association aux clients ⚠️ (dépend du parsing)
4. Résumé IA ⚠️ (clé Gemini manquante)
5. Stockage en BDD ⚠️ (dépend du parsing)

---

**Commencer par ces 3 fichiers dans cet ordre :**
1. `services/email_sync/email_parser.py` - Fix NoneType
2. `services/email_sync/ai_summarizer.py` - Fix clé Gemini  
3. `services/email_sync/email_sync_manager.py` - Fix format retour
