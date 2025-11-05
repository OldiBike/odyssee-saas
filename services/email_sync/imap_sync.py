"""
Service de synchronisation IMAP pour configuration manuelle
Compatible avec tous les serveurs IMAP (Hostinger, etc.)
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class IMAPSyncService:
    """Service de synchronisation via IMAP"""
    
    def __init__(self, imap_config):
        """
        Initialise le service IMAP
        
        Args:
            imap_config: Dict avec {host, port, username, password, use_ssl}
        """
        self.config = imap_config
        self.connection = None
    
    def _connect(self):
        """Établit la connexion IMAP"""
        try:
            if self.config.get('use_ssl', True):
                self.connection = imaplib.IMAP4_SSL(
                    self.config['host'],
                    int(self.config.get('port', 993))
                )
            else:
                self.connection = imaplib.IMAP4(
                    self.config['host'],
                    int(self.config.get('port', 143))
                )
                if self.config.get('use_tls', False):
                    self.connection.starttls()
            
            # Authentification
            self.connection.login(
                self.config['username'],
                self.config['password']
            )
            
            logger.info(f"Connecté à IMAP {self.config['host']}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur connexion IMAP: {e}")
            raise
    
    def _disconnect(self):
        """Ferme la connexion IMAP"""
        try:
            if self.connection:
                self.connection.logout()
                self.connection = None
        except:
            pass
    
    def test_connection(self):
        """Teste la connexion IMAP"""
        try:
            self._connect()
            self._disconnect()
            return True
        except:
            return False
    
    def get_new_messages(self, history_id=None, max_results=50):
        """
        Récupère les nouveaux messages
        
        Args:
            history_id: Non utilisé pour IMAP (on récupère les N derniers)
            max_results: Nombre max de messages à récupérer
            
        Returns:
            List d'IDs de messages
        """
        try:
            self._connect()
            
            # Sélectionner la boîte INBOX
            self.connection.select('INBOX')
            
            # Rechercher tous les messages (ou les N derniers)
            # Pour IMAP on peut filtrer par date si nécessaire
            _, message_numbers = self.connection.search(None, 'ALL')
            
            # Récupérer les IDs des messages
            message_ids = message_numbers[0].split()
            
            # Limiter au nombre max et prendre les plus récents
            message_ids = message_ids[-max_results:]
            
            self._disconnect()
            
            # Retourner les IDs sous forme de strings
            return [mid.decode() for mid in message_ids]
            
        except Exception as e:
            logger.error(f"Erreur get_new_messages: {e}")
            self._disconnect()
            return []
    
    def get_message_details(self, message_id):
        """
        Récupère les détails d'un message
        
        Args:
            message_id: ID du message
            
        Returns:
            Dict avec les détails du message
        """
        try:
            self._connect()
            self.connection.select('INBOX')
            
            # Récupérer le message
            _, msg_data = self.connection.fetch(message_id, '(RFC822)')
            
            # Parser l'email
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Extraire les headers
            subject = self._decode_header(email_message.get('Subject', ''))
            from_addr = self._decode_header(email_message.get('From', ''))
            to_addr = self._decode_header(email_message.get('To', ''))
            cc_addr = self._decode_header(email_message.get('Cc', ''))
            date_str = email_message.get('Date', '')
            
            # Parser la date
            try:
                msg_date = email.utils.parsedate_to_datetime(date_str)
            except:
                msg_date = datetime.utcnow()
            
            # Extraire le corps du message
            body = self._get_email_body(email_message)
            
            # Extraire l'ID du thread (Message-ID comme thread_id)
            thread_id = email_message.get('Message-ID', f'thread-{message_id}')
            
            self._disconnect()
            
            return {
                'id': message_id,
                'thread_id': thread_id,
                'subject': subject,
                'from': from_addr,
                'to': to_addr,
                'cc': cc_addr,
                'date': msg_date,
                'body': body,
                'is_sent': False  # Les messages IMAP INBOX sont reçus
            }
            
        except Exception as e:
            logger.error(f"Erreur get_message_details pour {message_id}: {e}")
            self._disconnect()
            raise
    
    def get_current_history_id(self):
        """
        Retourne un history_id (non utilisé pour IMAP)
        On pourrait utiliser UIDNEXT mais pour simplifier on retourne None
        """
        return None
    
    def _decode_header(self, header):
        """Décode un header d'email"""
        if not header:
            return ''
        
        decoded_parts = decode_header(header)
        decoded_str = ''
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_str += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_str += part
        
        return decoded_str
    
    def _get_email_body(self, email_message):
        """Extrait le corps du message email"""
        body = ''
        
        if email_message.is_multipart():
            # Message multipart (HTML + text généralement)
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))
                
                # Ignorer les pièces jointes
                if 'attachment' in content_disposition:
                    continue
                
                # Extraire le texte
                if content_type == 'text/plain':
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break  # Prendre le premier text/plain trouvé
                    except:
                        pass
                elif content_type == 'text/html' and not body:
                    # Fallback sur HTML si pas de text/plain
                    try:
                        html_body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        # Convertir HTML en texte (simple, pourrait être amélioré)
                        import re
                        body = re.sub('<[^<]+?>', '', html_body)
                    except:
                        pass
        else:
            # Message simple
            try:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                body = str(email_message.get_payload())
        
        return body.strip()
