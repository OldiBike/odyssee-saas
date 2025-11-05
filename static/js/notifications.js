/**
 * Système de notifications en temps réel pour Odyssée SaaS
 * Gère les notifications d'emails via SocketIO
 */

class NotificationManager {
    constructor() {
        this.socket = null;
        this.unreadCount = 0;
        this.init();
    }
    
    init() {
        // Se connecter au serveur SocketIO
        this.socket = io({
            transports: ['websocket', 'polling']
        });
        
        // Événements de connexion
        this.socket.on('connect', () => {
            console.log('✅ Connecté au serveur de notifications');
        });
        
        this.socket.on('disconnect', () => {
            console.log('❌ Déconnecté du serveur de notifications');
        });
        
        // Événement: compteur d'emails non lus
        this.socket.on('unread_count', (data) => {
            this.updateBadge(data.count);
        });
        
        // Événement: liste des emails récents
        this.socket.on('recent_emails', (data) => {
            this.populateDropdown(data.emails);
        });
        
        // Événement: nouvel email reçu
        this.socket.on('new_email', (data) => {
            this.handleNewEmail(data);
        });
        
        // Événement: email marqué comme lu
        this.socket.on('marked_read', (data) => {
            this.removeNotificationItem(data.interaction_id);
        });
        
        // Événement: tous les emails marqués comme lus
        this.socket.on('all_marked_read', (data) => {
            this.clearAllNotifications();
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
        
        // Afficher un toast
        this.showToast(data);
        
        // Notification desktop si permission accordée
        this.showDesktopNotification(data);
        
        // Ajouter à la liste dropdown
        this.addToDropdown(data);
    }
    
    showToast(data) {
        // Créer un toast de notification
        const toast = document.createElement('div');
        toast.className = 'fixed top-20 right-4 bg-white rounded-lg shadow-lg p-4 max-w-sm z-50 border-l-4 border-blue-500 animate-fade-in';
        toast.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    <i class="fas fa-envelope text-blue-500 text-xl"></i>
                </div>
                <div class="ml-3 flex-1">
                    <p class="text-sm font-medium text-gray-900">
                        ${this.escapeHtml(data.client_name)}
                    </p>
                    <p class="text-sm text-gray-500 mt-1">
                        ${this.escapeHtml(data.subject)}
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
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
    
    showDesktopNotification(data) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(`Nouvel email de ${data.client_name}`, {
                body: data.subject,
                icon: '/static/favicon.ico',
                tag: `email-${data.id}`
            });
        }
    }
    
    populateDropdown(emails) {
        const dropdown = document.getElementById('notifications-list');
        if (!dropdown) return;
        
        // Vider le contenu actuel
        dropdown.innerHTML = '';
        
        if (emails.length === 0) {
            dropdown.innerHTML = `
                <div class="px-4 py-8 text-center text-gray-500 text-sm">
                    <i class="fas fa-inbox text-3xl mb-2"></i>
                    <p>Aucune nouvelle notification</p>
                </div>
            `;
        } else {
            emails.forEach(email => {
                this.addEmailToDropdown(email, dropdown);
            });
        }
    }
    
    addToDropdown(data) {
        const dropdown = document.getElementById('notifications-list');
        if (!dropdown) return;
        
        // Si le dropdown est vide, le vider d'abord
        const emptyMessage = dropdown.querySelector('.text-gray-500');
        if (emptyMessage) {
            dropdown.innerHTML = '';
        }
        
        // Ajouter au début de la liste
        const emailItem = this.createEmailItem(data);
        dropdown.insertBefore(emailItem, dropdown.firstChild);
    }
    
    addEmailToDropdown(email, container) {
        const emailItem = this.createEmailItem(email);
        container.appendChild(emailItem);
    }
    
    createEmailItem(email) {
        const item = document.createElement('a');
        item.href = `/agency/crm/clients/${email.client_id}`;
        item.className = 'block px-4 py-3 hover:bg-gray-50 border-b border-gray-100 notification-item';
        item.dataset.interactionId = email.id;
        item.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    <i class="fas fa-envelope text-blue-500"></i>
                </div>
                <div class="ml-3 flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-900 truncate">
                        ${this.escapeHtml(email.client_name)}
                    </p>
                    <p class="text-xs text-gray-500 mt-1 truncate">
                        ${this.escapeHtml(email.subject)}
                    </p>
                    <p class="text-xs text-gray-400 mt-1">
                        ${this.formatTime(email.received_at)}
                    </p>
                </div>
            </div>
        `;
        
        // Marquer comme lu au clic
        item.addEventListener('click', (e) => {
            e.preventDefault();
            this.markAsRead(email.id);
            // Rediriger après un court délai
            setTimeout(() => {
                window.location.href = item.href;
            }, 100);
        });
        
        return item;
    }
    
    markAsRead(interactionId) {
        this.socket.emit('mark_read', { interaction_id: interactionId });
        this.unreadCount = Math.max(0, this.unreadCount - 1);
        this.updateBadge(this.unreadCount);
    }
    
    markAllAsRead() {
        this.socket.emit('mark_all_read');
    }
    
    removeNotificationItem(interactionId) {
        const item = document.querySelector(`[data-interaction-id="${interactionId}"]`);
        if (item) {
            item.remove();
            
            // Si plus d'items, afficher le message vide
            const dropdown = document.getElementById('notifications-list');
            if (dropdown && dropdown.children.length === 0) {
                this.populateDropdown([]);
            }
        }
    }
    
    clearAllNotifications() {
        this.populateDropdown([]);
    }
    
    formatTime(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000); // en secondes
        
        if (diff < 60) return 'À l\'instant';
        if (diff < 3600) return `Il y a ${Math.floor(diff / 60)} min`;
        if (diff < 86400) return `Il y a ${Math.floor(diff / 3600)} h`;
        
        // Formatage de la date
        const day = date.getDate().toString().padStart(2, '0');
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const year = date.getFullYear();
        return `${day}/${month}/${year}`;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    requestPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }
}

// Fonctions globales pour les boutons
function toggleNotifications() {
    const dropdown = document.getElementById('notifications-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('hidden');
    }
}

function markAllAsRead() {
    if (window.notificationManager) {
        window.notificationManager.markAllAsRead();
    }
}

// Initialiser au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    // Initialiser le gestionnaire de notifications
    window.notificationManager = new NotificationManager();
    
    // Demander la permission pour les notifications desktop
    window.notificationManager.requestPermission();
    
    // Fermer le dropdown au clic extérieur
    document.addEventListener('click', (e) => {
        const btn = document.getElementById('notifications-btn');
        const dropdown = document.getElementById('notifications-dropdown');
        
        if (btn && dropdown && !btn.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });
});
