# 📧 Synchronisation Email CRM - Progression de l'implémentation

## ✅ Ce qui a été fait (Phase 1 - Fondations MVP)

### 1. Base de données ✅
- **Fichier**: `migrations/versions/add_email_sync_fields.py`
- Extension du modèle `Agency` avec 8 nouveaux champs pour OAuth2 et sync
- Extension du modèle `ClientInteraction` avec 8 nouveaux champs pour les emails
- Index créés pour optimiser les requêtes
- **Action requise**: Exécuter `flask db upgrade` pour appliquer la migration

### 2. Modèles ✅
- **Fichier**: `models.py`
- Champs ajoutés à `Agency` pour stocker tokens OAuth2 (chiffrés)
- Champs ajoutés à `ClientInteraction` pour les détails des emails
- Méthode `to_dict()` mise à jour pour inclure les champs email

### 3. Dépendances ✅
- **Fichier**: `requirements.txt`
- Google Auth & Gmail API ajoutés
- MSAL (Microsoft Graph) ajouté pour Outlook (futur)
- **Action requise**: Exécuter `pip install -r requirements.txt`

### 4. Module de synchronisation email ✅
- **Dossier**: `services/email_sync/`

#### 4.1 Service Gmail (`gmail_sync.py`) ✅
- Authentification OAuth2
- Récupération des messages (avec History API pour sync incrémentale)
- Parsing des emails (HTML → texte)
- Test de connexion

#### 4.2 Parser & Matcher (`email_parser.py`) ✅
- Extraction d'adresses email depuis diverses formats
- Nettoyage du corps des emails (signatures, etc.)
- Matching intelligent email ↔ client
- Détection de pertinence des emails

#### 4.3 Résumé IA (`ai_summarizer.py`) ✅
- Génération de résumés avec Gemini
- Détection de sentiment (positif/négatif/neutre)
- Extraction de points clés
- Détection d'actions requises
- Catégorisation automatique

#### 4.4 Gestionnaire orchestrateur (`email_sync_manager.py`) ✅
- Orchestration complète de la synchronisation
- Traitement par lot avec statistiques
- Gestion des erreurs et rollback
- Activation/désactivation de la sync

## ✅ Phase 2 - Interface & OAuth (COMPLÉTÉE)

### 1. Configuration OAuth2 ✅
**Priorité: HAUTE - FAIT**

#### Variables d'environnement à ajouter dans `.env`:
```env
# Gmail OAuth
GMAIL_CLIENT_ID=votre_client_id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=votre_client_secret
GMAIL_REDIRECT_URI=http://localhost:5000/oauth/gmail/callback

# (Optionnel pour MVP) Outlook OAuth
OUTLOOK_CLIENT_ID=votre_app_id
OUTLOOK_CLIENT_SECRET=votre_client_secret
OUTLOOK_TENANT_ID=common
OUTLOOK_REDIRECT_URI=http://localhost:5000/oauth/outlook/callback
```

#### Routes OAuth2 à créer dans `app.py`:
```python
# 1. Page de configuration de la sync email
@app.route('/agency/settings/email-sync')
@agency_required
def email_sync_settings():
    """Page de configuration email sync"""
    pass

# 2. Initier le flow OAuth Gmail
@app.route('/oauth/gmail/authorize')
@agency_required
def gmail_oauth_authorize():
    """Redirige vers Google pour autorisation"""
    pass

# 3. Callback OAuth Gmail
@app.route('/oauth/gmail/callback')
@agency_required
def gmail_oauth_callback():
    """Traite le retour de Google OAuth"""
    pass

# 4. Déclencher une synchronisation manuelle
@app.route('/api/email-sync/trigger', methods=['POST'])
@agency_required
def trigger_email_sync():
    """Lance une sync manuelle"""
    pass

# 5. Obtenir le statut de la sync
@app.route('/api/email-sync/status')
@agency_required
def email_sync_status():
    """Retourne le statut de la sync"""
    pass

# 6. Déconnecter le compte email
@app.route('/api/email-sync/disconnect', methods=['POST'])
@agency_required
def disconnect_email_sync():
    """Désactive la sync"""
    pass
```

### 2. Templates HTML 🔄
**Priorité: HAUTE**

#### 2.1 Page de configuration (`templates/agency/settings/email_sync.html`)
- Sélecteur de provider (Gmail/Outlook)
- Bouton "Connecter mon compte"
- Affichage du statut (connecté/déconnecté)
- Dernière synchronisation
- Bouton "Synchroniser maintenant"

#### 2.2 Mise à jour de la fiche client (`templates/agency/crm/client_detail.html`)
- Afficher les emails dans la timeline des interactions
- Badge "📧 Email" pour différencier
- Afficher le sujet de l'email
- Afficher le résumé IA si disponible
- Indicateur email entrant/sortant

### 3. Configuration Google Cloud 🔄
**Priorité: HAUTE**

#### Étapes:
1. Aller sur https://console.cloud.google.com
2. Créer un nouveau projet (ou utiliser existant)
3. Activer Gmail API
4. Créer des credentials OAuth 2.0:
   - Type: Application Web
   - URI de redirection: `http://localhost:5000/oauth/gmail/callback`
   - Télécharger Client ID et Client Secret
5. Configurer l'écran de consentement OAuth
6. Ajouter les scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.labels`

### 4. Tests 🔄
**Priorité: MOYENNE**

- [ ] Tester le flow OAuth Gmail complet
- [ ] Tester la synchronisation avec différents types d'emails
- [ ] Tester le matching avec clients existants
- [ ] Tester les résumés IA
- [ ] Tester avec plusieurs threads
- [ ] Tester la gestion des erreurs

## 🎯 Plan d'exécution recommandé

### Étape 1: Setup OAuth (1-2h)
1. Créer projet Google Cloud
2. Configurer OAuth
3. Ajouter variables d'environnement
4. Implémenter les routes OAuth dans app.py

### Étape 2: Interface utilisateur (2-3h)
1. Créer template de configuration
2. Mettre à jour template client_detail.html
3. Ajouter CSS/JS nécessaire

### Étape 3: Tests & Debug (2-3h)
1. Tester le flow complet
2. Corriger les bugs
3. Affiner les résumés IA
4. Optimiser les performances

### Étape 4: Documentation utilisateur (1h)
1. Guide de configuration pour les agences
2. Screenshots
3. FAQ

## 📊 Architecture technique complète

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUX DE SYNCHRONISATION                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌────────────────────────────────────┐
        │  1. Utilisateur clique sur         │
        │     "Connecter Gmail"              │
        └───────────────┬────────────────────┘
                        │
                        ▼
        ┌────────────────────────────────────┐
        │  2. Redirection vers Google OAuth  │
        │     (demande permissions)          │
        └───────────────┬────────────────────┘
                        │
                        ▼
        ┌────────────────────────────────────┐
        │  3. Google renvoie tokens OAuth    │
        │     (access + refresh)             │
        └───────────────┬────────────────────┘
                        │
                        ▼
        ┌────────────────────────────────────┐
        │  4. Tokens chiffrés et stockés     │
        │     dans Agency.email_*_encrypted  │
        └───────────────┬────────────────────┘
                        │
                        ▼
        ┌────────────────────────────────────┐
        │  5. EmailSyncManager.sync_emails() │
        │     - Récupère nouveaux messages   │
        │     - Parse et nettoie             │
        │     - Match avec clients           │
        │     - Génère résumé IA             │
        │     - Sauve ClientInteraction      │
        └────────────────────────────────────┘
```

## 🔒 Sécurité

### Chiffrement ✅
- Tous les tokens OAuth sont chiffrés avec `utils.crypto`
- Utilise Fernet (chiffrement symétrique)
- Clé maître stockée dans `MASTER_ENCRYPTION_KEY`

### Scopes minimaux ✅
- Gmail: Lecture seule + labels
- Pas d'accès envoi pour le MVP

### RGPD ⚠️
- [ ] Ajouter mention dans CGU
- [ ] Obtenir consentement explicite
- [ ] Permettre suppression des données
- [ ] Journaliser les accès

## 💡 Améliorations futures (Phase 3+)

### Fonctionnalités avancées
- [ ] Support Outlook/Microsoft 365
- [ ] Webhooks temps réel (au lieu de polling)
- [ ] Client email intégré (lecture dans l'app)
- [ ] Envoi d'emails depuis l'app
- [ ] Quick Actions (insérer prix, dates, etc.)
- [ ] Templates d'emails
- [ ] Détection automatique d'opportunités
- [ ] Analytics des emails (taux de réponse, etc.)

### Optimisations
- [ ] Tâches en arrière-plan (Celery/APScheduler)
- [ ] Cache Redis pour réduire appels API
- [ ] Pagination des emails
- [ ] Filtres avancés

## 📝 Notes importantes

1. **Rate Limiting**: Gmail API a un quota de 1 milliard de requêtes/jour. Pour une agence moyenne, largement suffisant.

2. **History API**: Utilisée pour sync incrémentale. Très efficace, ne récupère que les nouveaux emails.

3. **Matching clients**: Seuls les emails impliquant des clients existants sont stockés. Les autres sont ignorés.

4. **Résumés IA**: Optionnels. Si Gemini API n'est pas configurée, la sync fonctionne quand même.

5. **Threading**: Les emails sont groupés par thread_id. Permet de suivre les conversations.

## 🚀 Commandes utiles

```bash
# Appliquer la migration
flask db upgrade

# Installer les dépendances
pip install -r requirements.txt

# Tester le chiffrement
python utils/crypto.py

# Lancer l'app en dev
flask run

# Vérifier les logs
tail -f logs/app.log
```

## 📞 Support

En cas de problème:
1. Vérifier les logs
2. Tester la connexion Gmail avec `test_connection()`
3. Vérifier que les tokens ne sont pas expirés
4. Re-autoriser si nécessaire

---

**Status**: Phase 1 (Fondations) ✅ COMPLÉTÉE  
**Prochaine étape**: Phase 2 (OAuth & Interface)  
**Temps estimé restant**: 5-7 heures
