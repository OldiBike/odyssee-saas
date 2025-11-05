# 📧 Implémentation de la Synchronisation Email pour le CRM

## 🎯 Objectif
Synchroniser automatiquement les emails échangés entre l'agence et ses clients pour alimenter l'historique des interactions dans le CRM.

## 🏗️ Architecture Proposée

### 1. Authentification OAuth2

#### Gmail API
- **Scopes nécessaires:**
  - `https://www.googleapis.com/auth/gmail.readonly` (lecture des emails)
  - `https://www.googleapis.com/auth/gmail.labels` (gestion des labels)
  
#### Microsoft Graph API (Outlook)
- **Scopes nécessaires:**
  - `Mail.Read` (lecture des emails)
  - `Mail.ReadBasic` (accès basique)

### 2. Stockage des Tokens

#### Extension du modèle Agency
```python
class Agency(db.Model):
    # ... champs existants ...
    
    # Configuration Email Sync
    email_sync_enabled = db.Column(db.Boolean, default=False)
    email_provider = db.Column(db.String(20))  # 'gmail' ou 'outlook'
    email_access_token_encrypted = db.Column(db.Text)  # Token OAuth chiffré
    email_refresh_token_encrypted = db.Column(db.Text)  # Refresh token chiffré
    email_token_expiry = db.Column(db.DateTime)
    email_sync_address = db.Column(db.String(255))  # Adresse email à synchroniser
    last_email_sync = db.Column(db.DateTime)
    email_sync_history_id = db.Column(db.String(100))  # Pour Gmail History API
```

#### Extension du modèle ClientInteraction
```python
class ClientInteraction(db.Model):
    # ... champs existants ...
    
    # Nouveau champs pour emails
    email_message_id = db.Column(db.String(255))  # ID unique de l'email
    email_thread_id = db.Column(db.String(255))  # ID du thread
    email_subject = db.Column(db.String(500))
    email_from = db.Column(db.String(255))
    email_to = db.Column(db.String(255))
    email_cc = db.Column(db.Text)
    is_outbound = db.Column(db.Boolean, default=False)  # True si envoyé par l'agence
    ai_summary = db.Column(db.Text)  # Résumé généré par IA
```

### 3. Service de Synchronisation

#### Structure du service
```
services/
└── email_sync/
    ├── __init__.py
    ├── gmail_sync.py      # Logique Gmail
    ├── outlook_sync.py    # Logique Outlook
    ├── email_parser.py    # Parsing et nettoyage des emails
    └── ai_summarizer.py   # Résumé IA avec Gemini
```

#### Workflow de synchronisation

```
┌─────────────────────────────────────────────────────────────┐
│                    SYNCHRONISATION EMAIL                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  1. Authentification  │
                │     OAuth2 Token      │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  2. Récupération des  │
                │  nouveaux emails      │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  3. Matching avec     │
                │  clients existants    │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  4. Parsing & Cleanup │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  5. Génération résumé │
                │     IA (Gemini)       │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  6. Enregistrement    │
                │  ClientInteraction    │
                └───────────────────────┘
```

## 📋 Plan d'Implémentation (Phases)

### Phase 1: Configuration OAuth (Prioritaire)
- [ ] Créer les routes d'authentification OAuth
- [ ] Page de configuration dans le dashboard admin
- [ ] Stockage sécurisé des tokens
- [ ] Gestion du refresh automatique des tokens

### Phase 2: Synchronisation Gmail
- [ ] Implémentation Gmail API
- [ ] Utilisation de Gmail History API pour synchronisation incrémentale
- [ ] Gestion des labels pour filtrer les emails pertinents
- [ ] Parsing des emails (HTML → texte)

### Phase 3: Synchronisation Outlook
- [ ] Implémentation Microsoft Graph API
- [ ] Delta query pour synchronisation incrémentale
- [ ] Gestion des dossiers Outlook

### Phase 4: Matching Intelligent
- [ ] Algorithme de matching email ↔ client
- [ ] Détection des threads de conversation
- [ ] Gestion des emails multi-destinataires

### Phase 5: Résumé IA
- [ ] Intégration Gemini pour résumé automatique
- [ ] Extraction des points clés
- [ ] Détection du sentiment (positif/négatif)

### Phase 6: Interface Utilisateur
- [ ] Affichage des emails dans la fiche client
- [ ] Filtres et recherche dans l'historique
- [ ] Bouton "Synchroniser maintenant"

### Phase 7: Automatisation
- [ ] Tâche en arrière-plan (Celery/APScheduler)
- [ ] Webhook Gmail/Outlook (optionnel)
- [ ] Notifications en cas d'erreur

## 🔒 Sécurité

### Considérations importantes
1. **Chiffrement des tokens**: Utiliser le système de chiffrement existant
2. **Scopes minimaux**: Ne demander que les permissions nécessaires
3. **Validation des emails**: Vérifier l'authenticité des expéditeurs
4. **Rate limiting**: Respecter les quotas API
5. **RGPD**: Obtenir le consentement pour stocker les emails

## 📊 Quotas API

### Gmail API
- 1 milliard de requêtes/jour (quota par défaut)
- 250 requêtes/seconde/utilisateur

### Microsoft Graph
- 10 000 requêtes/10 minutes/app
- Throttling possible si dépassement

## 📨 CLIENT EMAIL INTÉGRÉ (FEATURE AVANCÉE)

### Vue d'ensemble
Transformer l'application en un véritable client email avec des fonctionnalités intelligentes spécifiques aux agences de voyages.

### Fonctionnalités principales

#### 1. Lecture des emails dans l'app ✅
- Interface type Gmail/Outlook
- Threads de conversation
- Pièces jointes
- Recherche et filtres

#### 2. Envoi d'emails depuis l'app 📤
- Composer un nouvel email
- Répondre / Répondre à tous / Transférer
- CC / BCC
- Pièces jointes
- Envoi via Gmail API ou Microsoft Graph

#### 3. Éditeur intelligent pour agences de voyages 🎯

**Système de Quick Actions**
```
┌─────────────────────────────────────────────────────┐
│ Composer un email à: client@example.com             │
├─────────────────────────────────────────────────────┤
│ Sujet: Votre voyage à Rome                          │
├─────────────────────────────────────────────────────┤
│                                                      │
│ Bonjour M. Dupont,                                  │
│                                                      │
│ [📌 Quick Actions]                                  │
│ ┌──────────────┬──────────────┬──────────────┐    │
│ │ 💰 Prix      │ 📅 Dates     │ 🏨 Hôtel     │    │
│ ├──────────────┼──────────────┼──────────────┤    │
│ │ ✈️ Vol       │ 🗺️ Programme │ 📄 PDF       │    │
│ ├──────────────┼──────────────┼──────────────┤    │
│ │ 💳 Paiement  │ ⭐ Avis      │ 🤖 IA        │    │
│ └──────────────┴──────────────┴──────────────┘    │
│                                                      │
│ [Votre message ici...]                              │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Quick Actions disponibles:**

1. **💰 Insérer le prix**
   - Détecte automatiquement le voyage lié au client
   - Insère un bloc formaté avec le prix et les détails
   - Exemple: "Le tarif pour ce voyage est de 1 250€ par personne"

2. **📅 Insérer les dates**
   - Sélectionne un voyage du client
   - Insère les dates de départ/retour formatées

3. **🏨 Insérer info hôtel**
   - Nom de l'hôtel, adresse, étoiles
   - Lien Google Maps
   - Photos

4. **✈️ Insérer détails du vol**
   - Horaires de départ/arrivée
   - Numéro de vol
   - Compagnie aérienne

5. **🗺️ Insérer le programme**
   - Programme jour par jour
   - Formaté et lisible

6. **📄 Joindre le PDF**
   - Génère et joint automatiquement le PDF du voyage
   - Un clic et c'est fait

7. **💳 Insérer lien de paiement**
   - Génère un lien Stripe si nécessaire
   - Texte personnalisé avec montant

8. **⭐ Demander un avis**
   - Template pré-rempli pour demander un témoignage
   - Lien vers formulaire d'avis

9. **🤖 Suggérer avec IA**
   - Gemini analyse le contexte et suggère une réponse
   - Personnalisable avant envoi

### Architecture technique

#### Extension des modèles

```python
class EmailDraft(db.Model):
    """Brouillons d'emails"""
    id = db.Column(db.Integer, primary_key=True)
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'))  # Voyage lié
    
    to_address = db.Column(db.String(255))
    cc_address = db.Column(db.Text)
    bcc_address = db.Column(db.Text)
    subject = db.Column(db.String(500))
    body = db.Column(db.Text)
    attachments = db.Column(db.JSON)  # Liste des pièces jointes
    
    in_reply_to = db.Column(db.String(255))  # ID du message auquel on répond
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

class EmailTemplate(db.Model):
    """Templates d'emails pour l'agence"""
    id = db.Column(db.Integer, primary_key=True)
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id'))
    
    name = db.Column(db.String(100))
    subject_template = db.Column(db.String(500))
    body_template = db.Column(db.Text)
    
    # Variables disponibles: {client_name}, {trip_destination}, {price}, etc.
    variables = db.Column(db.JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### Service d'envoi d'emails

```python
# services/email_sync/email_sender.py
class EmailSender:
    def __init__(self, agency):
        self.agency = agency
        self.provider = agency.email_provider
        
    def send_email(self, to, subject, body, attachments=None, in_reply_to=None):
        """Envoie un email via Gmail ou Outlook API"""
        if self.provider == 'gmail':
            return self._send_via_gmail(to, subject, body, attachments, in_reply_to)
        elif self.provider == 'outlook':
            return self._send_via_outlook(to, subject, body, attachments, in_reply_to)
    
    def _send_via_gmail(self, to, subject, body, attachments, in_reply_to):
        """Envoie via Gmail API"""
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import base64
        
        message = MIMEMultipart()
        message['To'] = to
        message['Subject'] = subject
        
        if in_reply_to:
            message['In-Reply-To'] = in_reply_to
            message['References'] = in_reply_to
        
        msg_body = MIMEText(body, 'html')
        message.attach(msg_body)
        
        # Gérer les pièces jointes
        if attachments:
            for attachment in attachments:
                # Code pour attacher les fichiers
                pass
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        service = self._get_gmail_service()
        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        
        return sent_message['id']
```

#### Générateur de contenu intelligent

```python
# services/email_sync/content_generator.py
class EmailContentGenerator:
    """Génère du contenu formaté pour les emails"""
    
    def generate_price_block(self, trip):
        """Génère un bloc HTML avec le prix"""
        return f"""
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin: 0 0 10px 0; color: #2c3e50;">💰 Tarif</h3>
            <p style="font-size: 24px; font-weight: bold; color: #27ae60; margin: 10px 0;">
                {trip.price}€ par personne
            </p>
            <p style="margin: 5px 0; color: #7f8c8d;">
                Ce tarif inclut le vol, l'hébergement et les activités mentionnées
            </p>
        </div>
        """
    
    def generate_dates_block(self, trip):
        """Génère un bloc avec les dates"""
        trip_data = json.loads(trip.full_data_json)
        date_start = trip_data['form_data'].get('date_start')
        date_end = trip_data['form_data'].get('date_end')
        
        return f"""
        <div style="background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin: 0 0 10px 0; color: #2c3e50;">📅 Dates</h3>
            <p style="margin: 5px 0;">
                <strong>Départ:</strong> {date_start}
            </p>
            <p style="margin: 5px 0;">
                <strong>Retour:</strong> {date_end}
            </p>
        </div>
        """
    
    def generate_program_block(self, trip):
        """Génère le programme formaté"""
        trip_data = json.loads(trip.full_data_json)
        program = trip_data.get('program', [])
        
        html = """
        <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin: 0 0 15px 0; color: #2c3e50;">🗺️ Programme</h3>
        """
        
        for day in program:
            html += f"""
            <div style="margin-bottom: 15px;">
                <h4 style="color: #e74c3c; margin: 5px 0;">{day['title']}</h4>
                <p style="margin: 5px 0;">{day['description']}</p>
            </div>
            """
        
        html += "</div>"
        return html
    
    def generate_payment_link_block(self, trip):
        """Génère un bloc avec le lien de paiement"""
        if not trip.stripe_payment_link:
            return ""
        
        return f"""
        <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
            <h3 style="margin: 0 0 15px 0; color: #2c3e50;">💳 Paiement sécurisé</h3>
            <p style="margin: 10px 0;">
                Pour réserver ce voyage, vous pouvez effectuer le paiement en ligne de manière sécurisée:
            </p>
            <a href="{trip.stripe_payment_link}" 
               style="display: inline-block; background: #28a745; color: white; padding: 15px 30px; 
                      text-decoration: none; border-radius: 5px; font-weight: bold; margin: 10px 0;">
                Payer {trip.down_payment_amount}€ (acompte)
            </a>
        </div>
        """
```

### Interface utilisateur

#### 1. Inbox intégré dans l'app

```html
<!-- templates/agency/crm/inbox.html -->
<div class="email-client">
    <!-- Sidebar avec la liste des emails -->
    <div class="email-sidebar">
        <div class="email-folders">
            <div class="folder active">
                📥 Boîte de réception (23)
            </div>
            <div class="folder">
                📤 Envoyés
            </div>
            <div class="folder">
                ⭐ Suivis
            </div>
            <div class="folder">
                🗑️ Corbeille
            </div>
        </div>
        
        <div class="email-list">
            {% for email in emails %}
            <div class="email-item {% if email.unread %}unread{% endif %}" 
                 onclick="openEmail({{ email.id }})">
                <div class="email-from">{{ email.from_name }}</div>
                <div class="email-subject">{{ email.subject }}</div>
                <div class="email-preview">{{ email.preview }}</div>
                <div class="email-time">{{ email.time }}</div>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <!-- Panneau de lecture -->
    <div class="email-reader">
        <div id="email-content">
            <!-- Contenu de l'email sélectionné -->
        </div>
        
        <div class="email-actions">
            <button onclick="replyEmail()">↩️ Répondre</button>
            <button onclick="forwardEmail()">➡️ Transférer</button>
            <button onclick="deleteEmail()">🗑️ Supprimer</button>
        </div>
    </div>
</div>
```

#### 2. Éditeur avec Quick Actions

```html
<!-- templates/agency/crm/compose_email.html -->
<div class="email-composer">
    <div class="email-header">
        <input type="text" id="email-to" placeholder="À:">
        <input type="text" id="email-subject" placeholder="Sujet:">
    </div>
    
    <!-- Quick Actions Bar -->
    <div class="quick-actions-bar">
        <h4>📌 Quick Actions</h4>
        <div class="quick-actions-grid">
            <button onclick="insertPrice()">💰 Prix</button>
            <button onclick="insertDates()">📅 Dates</button>
            <button onclick="insertHotel()">🏨 Hôtel</button>
            <button onclick="insertFlight()">✈️ Vol</button>
            <button onclick="insertProgram()">🗺️ Programme</button>
            <button onclick="attachPDF()">📄 PDF</button>
            <button onclick="insertPaymentLink()">💳 Paiement</button>
            <button onclick="insertReview()">⭐ Avis</button>
            <button onclick="aiSuggest()">🤖 IA</button>
        </div>
    </div>
    
    <!-- Éditeur riche -->
    <div id="email-editor" contenteditable="true">
        <!-- Contenu HTML éditable -->
    </div>
    
    <!-- Actions -->
    <div class="email-composer-footer">
        <button onclick="saveDraft()">💾 Brouillon</button>
        <button onclick="sendEmail()" class="btn-primary">📤 Envoyer</button>
    </div>
</div>

<script>
function insertPrice() {
    // Récupérer le voyage lié au client
    const tripId = getCurrentTripId();
    
    fetch(`/api/trips/${tripId}/price-block`)
        .then(r => r.json())
        .then(data => {
            insertHTMLAtCursor(data.html);
        });
}

function insertProgram() {
    const tripId = getCurrentTripId();
    
    fetch(`/api/trips/${tripId}/program-block`)
        .then(r => r.json())
        .then(data => {
            insertHTMLAtCursor(data.html);
        });
}

function aiSuggest() {
    const context = {
        client_name: getCurrentClientName(),
        trip_destination: getCurrentTripDestination(),
        email_history: getEmailHistory()
    };
    
    fetch('/api/ai/suggest-email', {
        method: 'POST',
        body: JSON.stringify(context)
    })
    .then(r => r.json())
    .then(data => {
        // Afficher la suggestion dans un modal
        showAISuggestion(data.suggestion);
    });
}

function insertHTMLAtCursor(html) {
    const editor = document.getElementById('email-editor');
    const selection = window.getSelection();
    const range = selection.getRangeAt(0);
    
    const fragment = range.createContextualFragment(html);
    range.insertNode(fragment);
}
</script>
```

### Routes API nécessaires

```python
# Dans app.py

@app.route('/agency/crm/inbox')
@agency_required
def email_inbox():
    """Page inbox intégrée"""
    # Récupérer les emails depuis Gmail/Outlook
    return render_template('agency/crm/inbox.html')

@app.route('/api/emails/send', methods=['POST'])
@agency_required
def send_email():
    """Envoie un email via Gmail/Outlook API"""
    data = request.get_json()
    
    from services.email_sync.email_sender import EmailSender
    sender = EmailSender(g.agency)
    
    message_id = sender.send_email(
        to=data['to'],
        subject=data['subject'],
        body=data['body'],
        attachments=data.get('attachments'),
        in_reply_to=data.get('in_reply_to')
    )
    
    # Enregistrer dans ClientInteraction
    client = Client.query.filter_by(
        agency_id=g.agency.id,
        email=data['to']
    ).first()
    
    if client:
        interaction = ClientInteraction(
            client_id=client.id,
            user_id=g.user.id,
            interaction_type='email',
            content=data['body'],
            email_message_id=message_id,
            email_subject=data['subject'],
            is_outbound=True
        )
        db.session.add(interaction)
        db.session.commit()
    
    return jsonify({'success': True, 'message_id': message_id})

@app.route('/api/trips/<int:trip_id>/price-block')
@agency_required
def get_price_block(trip_id):
    """Génère le bloc HTML du prix"""
    trip = Trip.query.get_or_404(trip_id)
    
    from services.email_sync.content_generator import EmailContentGenerator
    generator = EmailContentGenerator()
    
    html = generator.generate_price_block(trip)
    return jsonify({'html': html})

@app.route('/api/trips/<int:trip_id>/program-block')
@agency_required
def get_program_block(trip_id):
    """Génère le bloc HTML du programme"""
    trip = Trip.query.get_or_404(trip_id)
    
    from services.email_sync.content_generator import EmailContentGenerator
    generator = EmailContentGenerator()
    
    html = generator.generate_program_block(trip)
    return jsonify({'html': html})

@app.route('/api/ai/suggest-email', methods=['POST'])
@agency_required
def ai_suggest_email():
    """IA suggère un email personnalisé"""
    data = request.get_json()
    
    prompt = f"""
    Tu es un assistant pour une agence de voyages.
    Rédige un email professionnel et chaleureux pour ce contexte:
    
    Client: {data['client_name']}
    Voyage: {data['trip_destination']}
    Historique: {data['email_history'][:500]}
    
    L'email doit être personnalisé, professionnel mais amical.
    """
    
    gemini_key = get_gemini_api_key()
    # Appeler Gemini...
    
    return jsonify({'suggestion': suggested_email})
```

## 💡 Fonctionnalités Avancées (Future)

### Suggestions d'actions
- Détecter les demandes de devis dans les emails
- Suggérer de créer un voyage automatiquement
- Rappeler les relances à faire

### Analytics
- Temps de réponse moyen
- Taux de conversion email → vente
- Analyse des sentiments clients

### Automatisation
- Réponses automatiques aux questions fréquentes
- Classification automatique des emails (demande, réclamation, etc.)
- Création automatique de tâches selon le contenu

### Smart Features
- **Auto-complétion intelligente**: Suggère la fin de la phrase basée sur le contexte
- **Templates intelligents**: Templates qui s'adaptent au contexte du client
- **Détection d'urgence**: Marque les emails urgents automatiquement
- **Follow-up automatique**: Rappelle de relancer si pas de réponse sous X jours

## 🚀 Quick Start (Pour les développeurs)

### 1. Configuration Gmail API

```bash
# Installer les dépendances
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# Créer un projet Google Cloud
# 1. Aller sur console.cloud.google.com
# 2. Créer un nouveau projet
# 3. Activer Gmail API
# 4. Créer des credentials OAuth 2.0
# 5. Télécharger credentials.json
```

### 2. Configuration Outlook API

```bash
# Installer les dépendances
pip install msal requests

# Créer une app Azure AD
# 1. Aller sur portal.azure.com
# 2. Azure Active Directory > App registrations
# 3. New registration
# 4. Configurer les permissions Microsoft Graph
# 5. Copier Client ID et Client Secret
```

### 3. Variables d'environnement (.env)

```env
# Gmail OAuth
GMAIL_CLIENT_ID=your_client_id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your_client_secret
GMAIL_REDIRECT_URI=http://localhost:5000/oauth/gmail/callback

# Outlook OAuth
OUTLOOK_CLIENT_ID=your_app_id
OUTLOOK_CLIENT_SECRET=your_client_secret
OUTLOOK_TENANT_ID=common
OUTLOOK_REDIRECT_URI=http://localhost:5000/oauth/outlook/callback

# Pour les résumés IA
GEMINI_API_KEY=your_gemini_key
```

## 📖 Exemples de Code

### Service Gmail

```python
# services/email_sync/gmail_sync.py
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from email import message_from_bytes

class GmailSyncService:
    def __init__(self, access_token, refresh_token):
        self.creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.getenv('GMAIL_CLIENT_ID'),
            client_secret=os.getenv('GMAIL_CLIENT_SECRET')
        )
        self.service = build('gmail', 'v1', credentials=self.creds)
    
    def get_new_messages(self, history_id=None):
        """Récupère les nouveaux messages depuis le dernier sync"""
        if history_id:
            # Utiliser History API pour synchronisation incrémentale
            results = self.service.users().history().list(
                userId='me',
                startHistoryId=history_id,
                historyTypes=['messageAdded']
            ).execute()
            
            messages = []
            for history in results.get('history', []):
                for msg in history.get('messagesAdded', []):
                    messages.append(msg['message']['id'])
        else:
            # Premier sync: récupérer les N derniers messages
            results = self.service.users().messages().list(
                userId='me',
                maxResults=100,
                q='after:2024/01/01'  # Personnalisable
            ).execute()
            messages = [msg['id'] for msg in results.get('messages', [])]
        
        return messages
    
    def get_message_details(self, message_id):
        """Récupère les détails d'un message"""
        message = self.service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        # Parser les headers
        headers = {h['name']: h['value'] for h in message['payload']['headers']}
        
        # Extraire le corps du message
        body = self._get_message_body(message['payload'])
        
        return {
            'id': message['id'],
            'thread_id': message['threadId'],
            'subject': headers.get('Subject', ''),
            'from': headers.get('From', ''),
            'to': headers.get('To', ''),
            'cc': headers.get('Cc', ''),
            'date': headers.get('Date', ''),
            'body': body
        }
    
    def _get_message_body(self, payload):
        """Extrait le corps du message (gère HTML et plaintext)"""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    return base64.urlsafe_b64decode(data).decode('utf-8')
        elif 'body' in payload:
            data = payload['body'].get('data', '')
            return base64.urlsafe_b64decode(data).decode('utf-8')
        return ''
```

### Matching des emails avec les clients

```python
# services/email_sync/email_parser.py
from models import Client
from sqlalchemy import or_

class EmailMatcher:
    @staticmethod
    def find_client_from_email(email_address, agency_id):
        """Trouve un client à partir d'une adresse email"""
        # Nettoyer l'adresse email
        email = email_address.lower().strip()
        if '<' in email:
            # Extraire l'email de "Name <email@domain.com>"
            email = email.split('<')[1].split('>')[0].strip()
        
        # Chercher un client avec cet email
        client = Client.query.filter_by(
            agency_id=agency_id,
            email=email
        ).first()
        
        return client
    
    @staticmethod
    def extract_emails_from_string(email_string):
        """Extrait toutes les adresses email d'une chaîne"""
        import re
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return re.findall(email_pattern, email_string)
```

### Résumé IA avec Gemini

```python
# services/email_sync/ai_summarizer.py
import google.generativeai as genai

class EmailSummarizer:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    def summarize_email(self, email_body, email_subject):
        """Génère un résumé concis de l'email"""
        prompt = f"""
        Résume cet email en 2-3 phrases courtes et précises.
        Focus sur les points clés et actions demandées.
        
        Sujet: {email_subject}
        
        Contenu:
        {email_body[:2000]}  # Limiter pour éviter les tokens excessifs
        
        Résumé:
        """
        
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def detect_sentiment(self, email_body):
        """Détecte le sentiment de l'email (positif/négatif/neutre)"""
        prompt = f"""
        Analyse le sentiment de cet email.
        Réponds uniquement par: "positif", "négatif" ou "neutre"
        
        Email:
        {email_body[:1000]}
        
        Sentiment:
        """
        
        response = self.model.generate_content(prompt)
        sentiment = response.text.strip().lower()
        
        if sentiment in ['positif', 'négatif', 'neutre']:
            return sentiment
        return 'neutre'
```

## 🎨 Interface Utilisateur

### Page de configuration (Admin)

```html
<!-- templates/agency/settings/email_sync.html -->
<div class="card">
    <h3>📧 Synchronisation Email</h3>
    
    <div class="form-group">
        <label>Fournisseur Email</label>
        <select id="email-provider">
            <option value="">-- Sélectionner --</option>
            <option value="gmail">Gmail</option>
            <option value="outlook">Outlook</option>
        </select>
    </div>
    
    <button id="connect-email-btn" class="btn btn-primary">
        🔗 Connecter mon compte email
    </button>
    
    <div id="sync-status" style="display:none;">
        <p>✅ Connecté: <strong id="sync-email"></strong></p>
        <p>📅 Dernière synchronisation: <span id="last-sync"></span></p>
        <button id="sync-now-btn" class="btn btn-secondary">
            🔄 Synchroniser maintenant
        </button>
        <button id="disconnect-btn" class="btn btn-danger">
            ❌ Déconnecter
        </button>
    </div>
</div>
```

### Affichage dans la fiche client

```html
<!-- Ajout dans templates/agency/crm/client_detail.html -->
<div class="interactions-timeline">
    {% for interaction in interactions %}
    <div class="interaction-item {% if interaction.interaction_type == 'email' %}interaction-email{% endif %}">
        <div class="interaction-icon">
            {% if interaction.interaction_type == 'email' %}
                📧
            {% else %}
                📝
            {% endif %}
        </div>
        
        <div class="interaction-content">
            <div class="interaction-header">
                <strong>{{ interaction.user_pseudo }}</strong>
                <span class="interaction-type">{{ interaction.interaction_type }}</span>
                <span class="interaction-date">{{ interaction.created_at }}</span>
            </div>
            
            {% if interaction.interaction_type == 'email' %}
                <div class="email-subject">
                    <strong>{{ interaction.email_subject }}</strong>
                </div>
                {% if interaction.ai_summary %}
                    <div class="ai-summary">
                        🤖 Résumé IA: {{ interaction.ai_summary }}
                    </div>
                {% endif %}
            {% endif %}
            
            <div class="interaction-body">
                {{ interaction.content }}
            </div>
        </div>
    </div>
    {% endfor %}
</div>
```

## ⚠️ Limitations et Considérations

### Limitations techniques
1. **Quota API**: Limiter la fréquence de synchronisation
2. **Taille des emails**: Résumer/tronquer les emails très longs
3. **Pièces jointes**: Non supportées dans v1 (optionnel future)
4. **Performance**: Synchronisation asynchrone obligatoire

### Considérations légales
1. **RGPD**: Obtenir le consentement explicite
2. **Confidentialité**: Chiffrer les données sensibles
3. **Droit à l'oubli**: Permettre la suppression des données
4. **Journalisation**: Tracker les accès aux données

## 📈 Métriques de Succès

### KPIs à suivre
- Nombre d'emails synchronisés par jour
- Taux de matching réussi (email → client)
- Temps moyen de synchronisation
- Taux d'erreur
- Utilisation par les vendeurs

## 🔄 Migration des Données

### Script de migration pour les clients existants
```python
# scripts/migrate_client_interactions.py
# À créer pour ajouter les nouveaux champs sans perdre de données
```

## 📚 Documentation API

### Routes à créer

```python
# Configuration OAuth
GET  /agency/settings/email-sync          # Page de configuration
POST /oauth/gmail/authorize               # Démarrer OAuth Gmail
GET  /oauth/gmail/callback               # Callback OAuth Gmail
POST /oauth/outlook/authorize            # Démarrer OAuth Outlook
GET  /oauth/outlook/callback            # Callback OAuth Outlook

# Synchronisation
POST /api/email-sync/trigger             # Déclencher sync manuelle
GET  /api/email-sync/status              # Statut de la sync
POST /api/email-sync/disconnect          # Déconnecter le compte

# Interactions
GET  /api/clients/<id>/interactions      # Récupérer les interactions (inclut emails)
```

## 🎯 Priorités d'Implémentation

### Version 1.0 (MVP)
1. Authentification OAuth Gmail
2. Synchronisation basique des emails
3. Matching simple par adresse email
4. Affichage dans la fiche client

### Version 2.0
1. Support Outlook
2. Résumés IA avec Gemini
3. Synchronisation incrémentale optimisée
4. Interface de configuration avancée

### Version 3.0
1. Détection automatique des opportunités
2. Analyse de sentiment
3. Suggestions d'actions
4. Webhooks en temps réel

## 💰 Coûts Estimés

### APIs
- **Gmail API**: Gratuit (jusqu'aux quotas)
- **Microsoft Graph**: Gratuit (licence Office 365 requise)
- **Gemini API**: Variable selon l'usage (~$0.001 par résumé)

### Infrastructure
- **Background tasks**: Nécessite Celery + Redis ou APScheduler
- **Stockage**: +10-20% de base de données

## ✅ Checklist Avant Production

- [ ] Tests OAuth Gmail et Outlook
- [ ] Gestion d'erreurs robuste
- [ ] Rate limiting respecté
- [ ] Chiffrement des tokens vérifié
- [ ] RGPD compliance
- [ ] Documentation utilisateur
- [ ] Formation des vendeurs
- [ ] Monitoring et alertes
- [ ] Backup et récupération
- [ ] Performance testée (100+ emails)

---

## 📞 Support

Pour toute question sur l'implémentation:
1. Consulter la documentation Gmail/Outlook API
2. Tester en environnement de développement
3. Valider avec un compte test avant production
