# 🔔 Système de Notifications Temps Réel - Plan d'Implémentation

## 📋 Vue d'Ensemble

**Objectif :** Implémenter un système de notifications en temps réel pour alerter les utilisateurs quand un client envoie un email.

**Technologies :** Flask-SocketIO + Redis (optionnel) + Frontend JavaScript

---

## 🎯 Fonctionnalités Requises

### 1. Badge de Notification dans la Navbar
- Afficher un compteur `🔔 (3)` des nouveaux emails non lus
- Mise à jour en temps réel sans refresh

### 2. Dropdown de Notifications
- Liste des 5 derniers emails reçus
- Cliquer pour ouvrir la fiche client correspondante
- Bouton "Tout marquer comme lu"

### 3. Notifications Push
- Popup toast quand nouvel email arrive
- Son de notification (optionnel)
- Permission navigateur pour notifications desktop

### 4. Persistance
- Marquer les emails comme "lus" dans la DB
- Conserver l'état entre les sessions

---

## 🔧 Architecture Technique

### Backend - Flask-SocketIO

**1. Installation**
```bash
pip install flask-socketio python-socketio redis
```

**2. Initialisation dans `app.py`**
```python
from flask_socketio import SocketIO, emit, join_room, leave_room

# Après l'initialisation de Flask
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# À la fin du fichier
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
```

**3. Événements SocketIO**

Créer `services/notification_service.py` :

```python
"""
Service de notifications en temps réel
"""
from flask_socketio import emit
from models import ClientInteraction, Client
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Gère l'envoi de notifications en temps réel"""
    
    @staticmethod
    def notify_new_email(agency_id: int, interaction_id: int):
        """
        Envoie une notification pour un nouvel email
        
        Args:
            agency_id: ID de l'agence
            interaction_id: ID de l'interaction email
        """
        from app import socketio
        
        try:
            # Récupérer les détails de l'email
            interaction = ClientInteraction.query.get(interaction_id)
            if not interaction:
                return
            
            client = Client.query.get(interaction.client_id)
            if not client:
                return
            
            # Préparer le payload de notification
            notification_data = {
                'id': interaction.id,
                'client_id': client.id,
                'client_name': f"{client.first_name} {client.last_name}",
                'client_email': client.email,
                'subject': interaction.email_subject or 'Sans sujet',
                'summary': interaction.ai_summary or interaction.content[:100],
                'received_at': interaction.created_at.isoformat(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Émettre vers tous les utilisateurs de l'agence
            room = f'agency_{agency_id}'
            socketio.emit('new_email', notification_data, room=room)
            
            logger.info(f"Notification envoyée pour l'email {interaction_id} à l'agence {agency_id}")
            
        except Exception as e:
            logger.error(f"Erreur envoi notification: {e}", exc_info=True)
    
    @staticmethod
    def get_unread_count(agency_id: int, user_id: int) -> int:
        """
        Compte les emails non lus pour un utilisateur
        
        Args:
            agency_id: ID de l'agence
            user_id: ID de l'utilisateur
            
        Returns:
            int: Nombre d'emails non lus
        """
        from models import db
        
        # Compter les interactions email non lues
        count = db.session.query(ClientInteraction).join(Client).filter(
            Client.agency_id == agency_id,
            ClientInteraction.interaction_type == 'email',
            ClientInteraction.is_outbound == False,
            ClientInteraction.is_read == False
        ).count()
        
        return count
    
    @staticmethod
    def mark_as_read(interaction_id: int, user_id: int) -> bool:
        """
        Marque un email comme lu
        
        Args:
            interaction_id: ID de l'interaction
            user_id: ID de l'utilisateur qui marque comme lu
            
        Returns:
            bool: True si succès
        """
        from models import db
        
        try:
            interaction = ClientInteraction.query.get(interaction_id)
            if not interaction:
                return False
            
            interaction.is_read = True
            interaction.read_at = datetime.utcnow()
            interaction.read_by_user_id = user_id
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Erreur mark as read: {e}", exc_info=True)
            db.session.rollback()
            return False
```

**4. Routes SocketIO dans `app.py`**

```python
@socketio.on('connect')
def handle_connect():
    """Quand un utilisateur se connecte"""
    if 'user_id' not in session:
        return False  # Refuser connexion non authentifiée
    
    user_id = session['user_id']
    agency_id = session.get('agency_id')
    
    if agency_id:
        # Rejoindre la room de son agence
        room = f'agency_{agency_id}'
        join_room(room)
        
        # Envoyer le compteur d'emails non lus
        from services.notification_service import NotificationService
        unread_count = NotificationService.get_unread_count(agency_id, user_id)
        
        emit('unread_count', {'count': unread_count})
        
        logger.info(f"User {user_id} connected to agency room {room}")


@socketio.on('disconnect')
def handle_disconnect():
    """Quand un utilisateur se déconnecte"""
    if 'agency_id' in session:
        room = f'agency_{session['agency_id']}'
        leave_room(room)
        logger.info(f"User disconnected from room {room}")


@socketio.on('mark_read')
def handle_mark_read(data):
    """Marque un email comme lu"""
    if 'user_id' not in session:
        return
    
    interaction_id = data.get('interaction_id')
    user_id = session['user_id']
    
    from services.notification_service import NotificationService
    success = NotificationService.mark_as_read(interaction_id, user_id)
    
    if success:
        emit('marked_read', {'interaction_id': interaction_id})
```

---

### Frontend - JavaScript + HTML

**1. Ajouter Socket.IO Client dans `templates/base.html`**

```html
<!-- Avant la fermeture de </body> -->
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
<script src="{{ url_for('static', filename='js/notifications.js') }}"></script>
```

**2. Créer `static/js/notifications.js`**

```javascript
/**
 * Système de notifications en temps réel
 */

class NotificationManager {
    constructor() {
        this.socket = null;
        this.unreadCount = 0;
        this.notificationSound = new Audio('/static/sounds/notification.mp3');
        this.init();
    }
    
    init() {
        // Se connecter au serveur SocketIO
        this.socket = io({
            transports: ['websocket', 'polling']
        });
        
        // Événements
        this.socket.on('connect', () => {
            console.log('✅ Connected to notification server');
        });
        
        this.socket.on('disconnect', () => {
            console.log('❌ Disconnected from notification server');
        });
        
        this.socket.on('unread_count', (data) => {
            this.updateBadge(data.count);
        });
        
        this.socket.on('new_email', (data) => {
            this.handleNewEmail(data);
        });
        
        this.socket.on('marked_read', (data) => {
            this.removeNotification(data.interaction_id);
        });
    }
    
    updateBadge(count) {
        this.unreadCount = count;
        const badge = document.getElementById('notification-badge');
        
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        }
    }
    
    handleNewEmail(data) {
        // Incrémenter le compteur
        this.unreadCount++;
        this.updateBadge(this.unreadCount);
        
        // Jouer le son
        this.playNotificationSound();
        
        // Afficher un toast
        this.showToast(data);
        
        // Notification desktop (si permission accordée)
        this.showDesktopNotification(data);
        
        // Ajouter à la liste dropdown
        this.addToDropdown(data);
    }
    
    playNotificationSound() {
        try {
            this.notificationSound.play().catch(e => {
                console.log('Could not play notification sound:', e);
            });
        } catch (e) {
            // Ignorer les erreurs de lecture audio
        }
    }
    
    showToast(data) {
        // Créer un toast Tailwind
        const toast = document.createElement('div');
        toast.className = 'fixed top-20 right-4 bg-white rounded-lg shadow-lg p-4 max-w-sm z-50 border-l-4 border-blue-500 animate-slide-in';
        toast.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    <i class="fas fa-envelope text-blue-500 text-xl"></i>
                </div>
                <div class="ml-3 flex-1">
                    <p class="text-sm font-medium text-gray-900">
                        ${data.client_name}
                    </p>
                    <p class="text-sm text-gray-500 mt-1">
                        ${data.subject}
                    </p>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" 
                        class="ml-4 text-gray-400 hover:text-gray-600">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Auto-remove après 5 secondes
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
    
    showDesktopNotification(data) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(`Nouvel email de ${data.client_name}`, {
                body: data.subject,
                icon: '/static/images/logo.png',
                tag: `email-${data.id}`
            });
        }
    }
    
    addToDropdown(data) {
        const dropdown = document.getElementById('notifications-dropdown');
        if (!dropdown) return;
        
        const item = document.createElement('a');
        item.href = `/agency/crm/clients/${data.client_id}`;
        item.className = 'block px-4 py-3 hover:bg-gray-50 border-b notification-item';
        item.dataset.interactionId = data.id;
        item.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    <i class="fas fa-envelope text-blue-500"></i>
                </div>
                <div class="ml-3 flex-1">
                    <p class="text-sm font-medium text-gray-900">${data.client_name}</p>
                    <p class="text-xs text-gray-500 mt-1">${data.subject}</p>
                    <p class="text-xs text-gray-400 mt-1">
                        ${this.formatTime(data.received_at)}
                    </p>
                </div>
            </div>
        `;
        
        // Ajouter au début de la liste
        dropdown.insertBefore(item, dropdown.firstChild);
        
        // Marquer comme lu au clic
        item.addEventListener('click', (e) => {
            this.markAsRead(data.id);
        });
    }
    
    markAsRead(interactionId) {
        this.socket.emit('mark_read', { interaction_id: interactionId });
        this.unreadCount = Math.max(0, this.unreadCount - 1);
        this.updateBadge(this.unreadCount);
    }
    
    removeNotification(interactionId) {
        const item = document.querySelector(`[data-interaction-id="${interactionId}"]`);
        if (item) {
            item.remove();
        }
    }
    
    formatTime(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000); // en secondes
        
        if (diff < 60) return 'À l\'instant';
        if (diff < 3600) return `Il y a ${Math.floor(diff / 60)} min`;
        if (diff < 86400) return `Il y a ${Math.floor(diff / 3600)} h`;
        return date.toLocaleDateString('fr-FR');
    }
    
    requestPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }
}

// Initialiser au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    window.notificationManager = new NotificationManager();
    
    // Demander la permission pour les notifications desktop
    window.notificationManager.requestPermission();
});
```

**3. Modifier `templates/base.html` - Navbar**

```html
<!-- Dans la navbar, après les autres éléments -->
<div class="relative ml-3">
    <!-- Bouton notifications -->
    <button id="notifications-btn" 
            class="relative text-gray-600 hover:text-gray-900 focus:outline-none"
            onclick="toggleNotifications()">
        <i class="fas fa-bell text-xl"></i>
        <!-- Badge de compteur -->
        <span id="notification-badge" 
              class="hidden absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
            0
        </span>
    </button>
    
    <!-- Dropdown de notifications -->
    <div id="notifications-dropdown" 
         class="hidden absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-xl z-50 border border-gray-200">
        <!-- En-tête -->
        <div class="px-4 py-3 border-b border-gray-200 flex justify-between items-center">
            <h3 class="text-sm font-semibold text-gray-900">Notifications</h3>
            <button onclick="markAllAsRead()" 
                    class="text-xs text-blue-600 hover:text-blue-800">
                Tout marquer comme lu
            </button>
        </div>
        
        <!-- Liste des notifications (remplie dynamiquement) -->
        <div id="notifications-list" class="max-h-96 overflow-y-auto">
            <!-- Les notifications apparaissent ici -->
            <div class="px-4 py-8 text-center text-gray-500 text-sm">
                <i class="fas fa-inbox text-3xl mb-2"></i>
                <p>Aucune nouvelle notification</p>
            </div>
        </div>
    </div>
</div>

<script>
function toggleNotifications() {
    const dropdown = document.getElementById('notifications-dropdown');
    dropdown.classList.toggle('hidden');
}

function markAllAsRead() {
    // Émettre un événement pour marquer tous comme lus
    if (window.notificationManager) {
        // Logique à implémenter
    }
}

// Fermer le dropdown au clic extérieur
document.addEventListener('click', (e) => {
    const btn = document.getElementById('notifications-btn');
    const dropdown = document.getElementById('notifications-dropdown');
    
    if (!btn.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.add('hidden');
    }
});
</script>
```

---

## 🔄 Intégration avec la Synchronisation Email

**Modifier `services/email_sync/email_sync_manager.py`**

Après avoir sauvegardé un nouvel email en DB :

```python
# Dans la méthode save_email_to_db ou équivalent
if new_interaction:
    db.session.add(new_interaction)
    db.session.commit()
    
    # Envoyer une notification en temps réel
    from services.notification_service import NotificationService
    NotificationService.notify_new_email(
        agency_id=self.agency.id,
        interaction_id=new_interaction.id
    )
```

---

## 📊 Migration Base de Données

**Ajouter les champs pour le tracking des lectures**

Créer `migrations/versions/add_notification_fields.py` :

```python
"""Add notification tracking fields

Revision ID: add_notification_fields
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('client_interactions', 
        sa.Column('is_read', sa.Boolean(), default=False))
    op.add_column('client_interactions', 
        sa.Column('read_at', sa.DateTime(), nullable=True))
    op.add_column('client_interactions', 
        sa.Column('read_by_user_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('client_interactions', 'read_by_user_id')
    op.drop_column('client_interactions', 'read_at')
    op.drop_column('client_interactions', 'is_read')
```

---

## ✅ Checklist d'Implémentation

### Backend
- [ ] Installer Flask-SocketIO
- [ ] Créer `services/notification_service.py`
- [ ] Ajouter les événements SocketIO dans `app.py`
- [ ] Modifier `email_sync_manager.py` pour émettre notifications
- [ ] Créer migration DB pour champs `is_read`, `read_at`, `read_by_user_id`
- [ ] Exécuter migration

### Frontend
- [ ] Ajouter Socket.IO client dans `base.html`
- [ ] Créer `static/js/notifications.js`
- [ ] Modifier navbar pour ajouter icône 🔔 + badge
- [ ] Créer dropdown de notifications
- [ ] Ajouter son de notification (optionnel)
- [ ] Tester les notifications en temps réel

### Tests
- [ ] Tester connexion SocketIO
- [ ] Envoyer un email test et vérifier notification
- [ ] Tester "marquer comme lu"
- [ ] Tester avec plusieurs utilisateurs simultanés
- [ ] Tester reconnexion après perte de connexion

---

## 🎨 Améliorations Optionnelles

1. **Filtres de notifications**
   - Par type (email, interaction, vente)
   - Par priorité (urgent, normal)

2. **Préférences utilisateur**
   - Activer/désactiver le son
   - Choisir les types de notifications

3. **Historique des notifications**
   - Page dédiée avec toutes les notifications
   - Recherche et filtres

4. **Notifications par email**
   - Digest quotidien des emails non lus
   - Alerte immédiate pour emails urgents

---

## 📚 Ressources

- [Flask-SocketIO Documentation](https://flask-socketio.readthedocs.io/)
- [Socket.IO Client JavaScript](https://socket.io/docs/v4/client-api/)
- [Notification API MDN](https://developer.mozilla.org/en-US/docs/Web/API/Notification)

---

**Prêt à implémenter dans une nouvelle conversation !** 🚀
