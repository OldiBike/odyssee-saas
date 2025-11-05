# Guide d'Implémentation - Configuration SMTP/IMAP Manuelle

**Date**: 30 octobre 2025  
**Objectif**: Permettre aux agences d'utiliser n'importe quel fournisseur email (OVH, Infomaniak, serveurs professionnels) via configuration SMTP/IMAP manuelle

---

## 🎯 Problème identifié

Le système actuel ne supporte que OAuth Gmail/Outlook. Les agences qui utilisent d'autres fournisseurs (OVH, Infomaniak, serveurs professionnels, etc.) ne peuvent pas utiliser la fonctionnalité email reply.

## ✅ Solution

Ajouter une option de configuration manuelle SMTP/IMAP avec :
- Serveur SMTP (envoi)
- Serveur IMAP (réception)
- Login/mot de passe
- Ports et SSL

---

## 📋 Étapes d'Implémentation

### 1. Migration Base de Données ✅ FAIT

Fichier créé : `migrations/versions/add_smtp_imap_config.py`

**Champs ajoutés à la table `agency`** :
- `smtp_config_encrypted` (Text) - Config SMTP chiffrée
- `imap_config_encrypted` (Text) - Config IMAP chiffrée
- `email_config_type` (String) - 'oauth' ou 'manual'

**Commande à exécuter** :
```bash
flask db upgrade
```

---

### 2. Modification du Service EmailSender

**Fichier**: `services/email_sync/email_sender.py`

#### A. Ajouter le support SMTP dans `__init__`

```python
def __init__(self, agency_id):
    self.agency_id = agency_id
    self.agency = Agency.query.get(agency_id)
    
    if not self.agency:
        raise EmailSendError(f"Agency {agency_id} not found")
    
    # Déterminer le type de configuration
    self.config_type = self.agency.email_config_type or 'oauth'
    
    if self.config_type == 'oauth':
        # Configuration OAuth existante (Gmail/Outlook)
        if not self.agency.email_sync_enabled:
            raise EmailSendError("Email sync not enabled for agency")
        
        self.provider = self.agency.email_provider
        self.access_token = self._get_access_token()
        
        if self.provider == 'gmail':
            self.service = self._init_gmail_service()
        elif self.provider == 'outlook':
            self.service = self._init_outlook_service()
        else:
            raise EmailSendError(f"Unsupported provider: {self.provider}")
    
    elif self.config_type == 'manual':
        # Configuration SMTP/IMAP manuelle
        self.smtp_config = self._load_smtp_config()
        self.imap_config = self._load_imap_config()
        
        if not self.smtp_config or not self.imap_config:
            raise EmailSendError("SMTP/IMAP config not found")
```

#### B. Ajouter les méthodes de chargement des configs

```python
def _load_smtp_config(self):
    """Charge et déchiffre la configuration SMTP"""
    from utils.crypto import decrypt_config
    
    if not self.agency.smtp_config_encrypted:
        return None
    
    config = decrypt_config(self.agency.smtp_config_encrypted)
    
    # Validation
    required_fields = ['host', 'port', 'username', 'password', 'from_email']
    if not all(field in config for field in required_fields):
        raise EmailSendError("Invalid SMTP config")
    
    return config

def _load_imap_config(self):
    """Charge et déchiffre la configuration IMAP"""
    from utils.crypto import decrypt_config
    
    if not self.agency.imap_config_encrypted:
        return None
    
    config = decrypt_config(self.agency.imap_config_encrypted)
    
    # Validation
    required_fields = ['host', 'port', 'username', 'password']
    if not all(field in config for field in required_fields):
        raise EmailSendError("Invalid IMAP config")
    
    return config
```

#### C. Modifier la méthode `send_email` pour supporter SMTP

```python
def send_email(self, to, subject, body, html_body=None, cc=None, bcc=None, 
               in_reply_to=None, references=None):
    """
    Envoie un email via OAuth ou SMTP selon la configuration
    """
    if self.config_type == 'oauth':
        # Code OAuth existant (Gmail/Outlook)
        return self._send_oauth_email(to, subject, body, html_body, cc, bcc, 
                                      in_reply_to, references)
    
    elif self.config_type == 'manual':
        # Nouveau : Envoi via SMTP
        return self._send_smtp_email(to, subject, body, html_body, cc, bcc, 
                                     in_reply_to, references)

def _send_smtp_email(self, to, subject, body, html_body=None, cc=None, bcc=None,
                     in_reply_to=None, references=None):
    """Envoie un email via SMTP"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.utils import formatdate, make_msgid
    
    try:
        # Créer le message
        msg = MIMEMultipart('alternative') if html_body else MIMEMultipart()
        msg['From'] = self.smtp_config['from_email']
        msg['To'] = to
        msg['Subject'] = subject
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid()
        
        # Threading
        if in_reply_to:
            msg['In-Reply-To'] = in_reply_to
        if references:
            msg['References'] = references
        
        # CC et BCC
        if cc:
            msg['Cc'] = cc
        
        # Corps du message
        if html_body:
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        else:
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Connexion SMTP
        use_ssl = self.smtp_config.get('use_ssl', True)
        
        if use_ssl:
            server = smtplib.SMTP_SSL(
                self.smtp_config['host'], 
                int(self.smtp_config['port'])
            )
        else:
            server = smtplib.SMTP(
                self.smtp_config['host'], 
                int(self.smtp_config['port'])
            )
            if self.smtp_config.get('use_tls', False):
                server.starttls()
        
        # Authentification
        server.login(
            self.smtp_config['username'], 
            self.smtp_config['password']
        )
        
        # Envoi
        recipients = [to]
        if cc:
            recipients.extend(cc.split(','))
        if bcc:
            recipients.extend(bcc.split(','))
        
        server.send_message(msg, to_addrs=recipients)
        server.quit()
        
        # Sauvegarder dans la base de données
        self._save_sent_email(
            to=to,
            subject=subject,
            body=body,
            message_id=msg['Message-ID'],
            thread_id=in_reply_to or msg['Message-ID']
        )
        
        return {
            'success': True,
            'message_id': msg['Message-ID'],
            'sent_at': datetime.now()
        }
        
    except smtplib.SMTPException as e:
        raise EmailSendError(f"SMTP error: {str(e)}")
    except Exception as e:
        raise EmailSendError(f"Email send error: {str(e)}")
```

---

### 3. Modification du Template

**Fichier**: `templates/agency/settings/email_sync.html`

#### A. Ajouter un sélecteur de type de configuration

Après la section d'en-tête, ajouter :

```html
<!-- Choix du type de configuration -->
<div class="bg-white rounded-xl shadow-md p-6 mb-6">
    <h2 class="text-xl font-bold text-gray-900 mb-4">
        <i class="fas fa-cog text-blue-600 mr-2"></i>
        Type de Configuration
    </h2>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="border-2 border-gray-200 rounded-lg p-4 cursor-pointer hover:border-blue-500 transition"
             onclick="selectConfigType('oauth')"
             id="oauth-card">
            <div class="flex items-center mb-2">
                <i class="fas fa-shield-alt text-blue-600 text-2xl mr-3"></i>
                <h3 class="font-bold text-lg">OAuth (Recommandé)</h3>
            </div>
            <p class="text-sm text-gray-600">Gmail ou Microsoft 365</p>
            <p class="text-xs text-gray-500 mt-2">Sécurisé et sans mot de passe</p>
        </div>
        
        <div class="border-2 border-gray-200 rounded-lg p-4 cursor-pointer hover:border-blue-500 transition"
             onclick="selectConfigType('manual')"
             id="manual-card">
            <div class="flex items-center mb-2">
                <i class="fas fa-server text-green-600 text-2xl mr-3"></i>
                <h3 class="font-bold text-lg">Configuration Manuelle</h3>
            </div>
            <p class="text-sm text-gray-600">SMTP/IMAP personnalisé</p>
            <p class="text-xs text-gray-500 mt-2">OVH, Infomaniak, serveurs pro</p>
        </div>
    </div>
</div>

<!-- Section OAuth (existante) -->
<div id="oauth-section" class="hidden">
    <!-- Contenu OAuth existant -->
</div>

<!-- Section SMTP/IMAP Manuel (NOUVEAU) -->
<div id="manual-section" class="hidden">
    <div class="bg-white rounded-xl shadow-md p-6 mb-6">
        <h2 class="text-xl font-bold text-gray-900 mb-4">
            <i class="fas fa-envelope-open-text text-green-600 mr-2"></i>
            Configuration SMTP/IMAP
        </h2>
        
        <form id="smtpConfigForm" class="space-y-6">
            <!-- Configuration SMTP (Envoi) -->
            <div class="border-l-4 border-green-500 pl-4">
                <h3 class="text-lg font-bold text-gray-900 mb-4">
                    📤 Serveur SMTP (Envoi)
                </h3>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Serveur SMTP *
                        </label>
                        <input type="text" name="smtp_host" required
                               class="w-full px-4 py-2 border border-gray-300 rounded-lg"
                               placeholder="smtp.example.com">
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Port *
                        </label>
                        <select name="smtp_port" required
                                class="w-full px-4 py-2 border border-gray-300 rounded-lg">
                            <option value="465">465 (SSL)</option>
                            <option value="587">587 (TLS)</option>
                            <option value="25">25 (Non sécurisé)</option>
                        </select>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Nom d'utilisateur *
                        </label>
                        <input type="text" name="smtp_username" required
                               class="w-full px-4 py-2 border border-gray-300 rounded-lg"
                               placeholder="votre@email.com">
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Mot de passe *
                        </label>
                        <input type="password" name="smtp_password" required
                               class="w-full px-4 py-2 border border-gray-300 rounded-lg"
                               placeholder="••••••••">
                    </div>
                    
                    <div class="md:col-span-2">
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Email d'envoi *
                        </label>
                        <input type="email" name="smtp_from_email" required
                               class="w-full px-4 py-2 border border-gray-300 rounded-lg"
                               placeholder="contact@votre-agence.com">
                        <p class="text-xs text-gray-500 mt-1">
                            Adresse qui apparaîtra comme expéditeur
                        </p>
                    </div>
                </div>
                
                <div class="mt-4 flex items-center">
                    <input type="checkbox" name="smtp_use_ssl" checked
                           class="mr-2">
                    <label class="text-sm text-gray-700">Utiliser SSL (recommandé)</label>
                </div>
            </div>
            
            <!-- Configuration IMAP (Réception) -->
            <div class="border-l-4 border-blue-500 pl-4">
                <h3 class="text-lg font-bold text-gray-900 mb-4">
                    📥 Serveur IMAP (Réception)
                </h3>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Serveur IMAP *
                        </label>
                        <input type="text" name="imap_host" required
                               class="w-full px-4 py-2 border border-gray-300 rounded-lg"
                               placeholder="imap.example.com">
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Port *
                        </label>
                        <select name="imap_port" required
                                class="w-full px-4 py-2 border border-gray-300 rounded-lg">
                            <option value="993">993 (SSL)</option>
                            <option value="143">143 (TLS)</option>
                        </select>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Nom d'utilisateur *
                        </label>
                        <input type="text" name="imap_username" required
                               class="w-full px-4 py-2 border border-gray-300 rounded-lg"
                               placeholder="votre@email.com">
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Mot de passe *
                        </label>
                        <input type="password" name="imap_password" required
                               class="w-full px-4 py-2 border border-gray-300 rounded-lg"
                               placeholder="••••••••">
                    </div>
                </div>
                
                <div class="mt-4 flex items-center">
                    <input type="checkbox" name="imap_use_ssl" checked
                           class="mr-2">
                    <label class="text-sm text-gray-700">Utiliser SSL (recommandé)</label>
                </div>
            </div>
            
            <!-- Boutons -->
            <div class="flex items-center space-x-4">
                <button type="submit" 
                        class="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition">
                    <i class="fas fa-save mr-2"></i>
                    Enregistrer la Configuration
                </button>
                
                <button type="button" onclick="testSmtpConnection()"
                        class="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition">
                    <i class="fas fa-vial mr-2"></i>
                    Tester la Connexion
                </button>
            </div>
        </form>
    </div>
</div>
```

#### B. Ajouter le JavaScript

```html
<script>
let currentConfigType = '{{ agency.email_config_type or "oauth" }}';

function selectConfigType(type) {
    currentConfigType = type;
    
    // Mettre à jour les cartes
    document.getElementById('oauth-card').classList.remove('border-blue-500', 'bg-blue-50');
    document.getElementById('manual-card').classList.remove('border-blue-500', 'bg-blue-50');
    
    if (type === 'oauth') {
        document.getElementById('oauth-card').classList.add('border-blue-500', 'bg-blue-50');
        document.getElementById('oauth-section').classList.remove('hidden');
        document.getElementById('manual-section').classList.add('hidden');
    } else {
        document.getElementById('manual-card').classList.add('border-blue-500', 'bg-blue-50');
        document.getElementById('manual-section').classList.remove('hidden');
        document.getElementById('oauth-section').classList.add('hidden');
    }
}

// Initialiser l'affichage au chargement
document.addEventListener('DOMContentLoaded', function() {
    selectConfigType(currentConfigType);
});

// Soumettre la configuration SMTP/IMAP
document.getElementById('smtpConfigForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const config = {
        smtp: {
            host: formData.get('smtp_host'),
            port: formData.get('smtp_port'),
            username: formData.get('smtp_username'),
            password: formData.get('smtp_password'),
            from_email: formData.get('smtp_from_email'),
            use_ssl: formData.get('smtp_use_ssl') === 'on'
        },
        imap: {
            host: formData.get('imap_host'),
            port: formData.get('imap_port'),
            username: formData.get('imap_username'),
            password: formData.get('imap_password'),
            use_ssl: formData.get('imap_use_ssl') === 'on'
        }
    };
    
    try {
        const response = await fetchWithCSRF('/api/email-sync/config-manual', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Configuration enregistrée avec succès', 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast(data.error || 'Erreur lors de l\'enregistrement', 'error');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showToast('Erreur réseau', 'error');
    }
});

// Tester la connexion
async function testSmtpConnection() {
    const formData = new FormData(document.getElementById('smtpConfigForm'));
    const config = {
        smtp: {
            host: formData.get('smtp_host'),
            port: formData.get('smtp_port'),
            username: formData.get('smtp_username'),
            password: formData.get('smtp_password')
        }
    };
    
    try {
        const response = await fetchWithCSRF('/api/email-sync/test-smtp', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('✅ Connexion SMTP réussie !', 'success');
        } else {
            showToast('❌ ' + (data.error || 'Échec de la connexion'), 'error');
        }
    } catch (error) {
        showToast('Erreur réseau', 'error');
    }
}
</script>
```

---

### 4. Routes API dans app.py

Ajouter ces routes après les routes email sync existantes :

```python
@app.route('/api/email-sync/config-manual', methods=['POST'])
@agency_admin_required
def api_save_manual_email_config():
    """Enregistre la configuration SMTP/IMAP manuelle"""
    from utils.crypto import encrypt_config
    
    data = request.get_json()
    smtp_config = data.get('smtp')
    imap_config = data.get('imap')
    
    if not smtp_config or not imap_config:
        return jsonify({
            'success': False,
            'error': 'Configuration SMTP et IMAP requises'
        }), 400
    
    try:
        # Chiffrer et sauvegarder
        g.agency.smtp_config_encrypted = encrypt_config(smtp_config)
        g.agency.imap_config_encrypted = encrypt_config(imap_config)
        g.agency.email_config_type = 'manual'
        g.agency.email_sync_enabled = True
        g.agency.email_provider = 'manual'
        
        db.session.commit()
        
        # Log de l'activité
        log_activity(
            action='email_config_manual',
            user_id=g.user.id,
            agency_id=g.agency.id,
            details='Configuration email manuelle SMTP/IMAP activée'
        )
        
        return jsonify({
            'success': True,
            'message': 'Configuration enregistrée avec succès'
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Erreur save manual config: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/email-sync/test-smtp', methods=['POST'])
@agency_admin_required
def api_test_smtp_connection():
    """Teste la connexion SMTP"""
    import smtplib
    
    data = request.get_json()
    smtp_config = data.get('smtp')
    
    if not smtp_config:
        return jsonify({
            'success': False,
            'error': 'Configuration SMTP requise'
        }), 400
    
    try:
        # Tenter une connexion
        use_ssl = smtp_config.get('use_ssl', True)
        
        if use_ssl:
            server = smtplib.SMTP_SSL(
                smtp_config['host'], 
                int(smtp_config['port']),
                timeout=10
            )
        else:
            server = smtplib.SMTP(
                smtp_config['host'], 
                int(smtp_config['port']),
                timeout=10
            )
        
        server.login(smtp_config['username'], smtp_config['password'])
        server.quit()
        
        return jsonify({
            'success': True,
            'message': 'Connexion SMTP réussie'
        })
        
    except smtplib.SMTPAuthenticationError:
        return jsonify({
            'success': False,
            'error': 'Erreur d\'authentification - Vérifiez le nom d\'utilisateur et le mot de passe'
        }), 400
    except smtplib.SMTPException as e:
        return jsonify({
            'success': False,
            'error': f'Erreur SMTP: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur de connexion: {str(e)}'
        }), 400
```

---

## 📖 Exemples de Configuration

### OVH
```
SMTP: ssl0.ovh.net (port 465, SSL)
IMAP: ssl0.ovh.net (port 993, SSL)
Username: votre@email.com
Password: votre_mot_de_passe
```

### Infomaniak
```
SMTP: mail.infomaniak.com (port 587, TLS)
IMAP: mail.infomaniak.com (port 993, SSL)
Username: votre@email.com
Password: votre_mot_de_passe
```

### Gmail (sans OAuth)
```
SMTP: smtp.gmail.com (port 587, TLS)
IMAP: imap.gmail.com (port 993, SSL)
Username: votre@gmail.com
Password: mot_de_passe_application (pas le mot de passe Gmail)
```

---

## ✅ Avantages de cette approche

1. **Universel** : Fonctionne avec n'importe quel fournisseur email
2. **Simple** : Pas de configuration OAuth complexe
3. **Contrôle** : L'utilisateur garde le contrôle total
4. **Compatible** : Serveurs professionnels, OVH, Infomaniak, etc.

## ⚠️ Sécurité

- Les mots de passe sont chiffrés en base de données avec Fernet
- Connexions SSL/TLS obligatoires par défaut
- Test de connexion avant sauvegarde
- Logs d'activité pour traçabilité

---

## 🧪 Tests à effectuer

1. ✅ Appliquer la migration
2. ✅ Configurer un compte email manuel (ex: OVH)
3. ✅ Tester la connexion SMTP
4. ✅ Envoyer un email de test
5. ✅ Synchroniser les emails entrants (IMAP)
6. ✅ Répondre à un email depuis la fiche client

---

**Status**: 📝 Documentation complète - Implémentation à finaliser
**Prochaine étape**: Modifier `email_sender.py` et `email_sync.html` selon ce guide
