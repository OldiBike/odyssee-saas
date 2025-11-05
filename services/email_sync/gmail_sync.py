"""
Service de synchronisation Gmail
Gère l'authentification OAuth2 et la récupération des emails depuis Gmail
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from email import message_from_bytes
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)


class GmailSyncService:
    """Service pour synchroniser les emails depuis Gmail via API"""
    
    def __init__(self, access_token, refresh_token=None):
        """
        Initialise le service Gmail
        
        Args:
            access_token: Token d'accès OAuth2
            refresh_token: Token de rafraîchissement (optionnel)
        """
        self.creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.getenv('GMAIL_CLIENT_ID'),
            client_secret=os.getenv('GMAIL_CLIENT_SECRET'),
            scopes=[
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.labels'
            ]
        )
        
        try:
            self.service = build('gmail', 'v1', credentials=self.creds)
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du service Gmail: {e}")
            raise
    
    def get_new_messages(self, history_id=None, max_results=100):
        """
        Récupère les nouveaux messages depuis le dernier sync
        
        Args:
            history_id: ID de l'historique pour sync incrémentale (optionnel)
            max_results: Nombre maximum de messages à récupérer
            
        Returns:
            Liste des IDs de messages
        """
        try:
            messages = []
            
            if history_id:
                # Utiliser History API pour synchronisation incrémentale
                logger.info(f"Synchronisation incrémentale depuis history_id: {history_id}")
                results = self.service.users().history().list(
                    userId='me',
                    startHistoryId=history_id,
                    historyTypes=['messageAdded']
                ).execute()
                
                for history in results.get('history', []):
                    for msg in history.get('messagesAdded', []):
                        messages.append(msg['message']['id'])
            else:
                # Premier sync: récupérer les N derniers messages
                logger.info(f"Premier sync: récupération des {max_results} derniers messages")
                results = self.service.users().messages().list(
                    userId='me',
                    maxResults=max_results,
                    q='after:2024/01/01'  # Ne récupérer que les emails récents
                ).execute()
                
                messages = [msg['id'] for msg in results.get('messages', [])]
            
            logger.info(f"{len(messages)} nouveaux messages trouvés")
            return messages
            
        except HttpError as e:
            logger.error(f"Erreur HTTP lors de la récupération des messages: {e}")
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des messages: {e}")
            raise
    
    def get_message_details(self, message_id):
        """
        Récupère les détails complets d'un message
        
        Args:
            message_id: ID du message Gmail
            
        Returns:
            Dict avec les détails du message
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Parser les headers
            headers = {}
            for header in message['payload']['headers']:
                headers[header['name']] = header['value']
            
            # Extraire le corps du message
            body = self._get_message_body(message['payload'])
            
            # Déterminer si c'est un email envoyé ou reçu
            labels = message.get('labelIds', [])
            is_sent = 'SENT' in labels
            
            # Timestamp
            timestamp = int(message['internalDate']) / 1000
            email_date = datetime.fromtimestamp(timestamp)
            
            return {
                'id': message['id'],
                'thread_id': message['threadId'],
                'subject': headers.get('Subject', '(Sans objet)'),
                'from': headers.get('From', ''),
                'to': headers.get('To', ''),
                'cc': headers.get('Cc', ''),
                'date': email_date,
                'body': body,
                'is_sent': is_sent,
                'labels': labels
            }
            
        except HttpError as e:
            logger.error(f"Erreur HTTP lors de la récupération du message {message_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du message {message_id}: {e}")
            raise
    
    def _get_message_body(self, payload):
        """
        Extrait le corps du message (gère HTML et plaintext)
        
        Args:
            payload: Payload du message Gmail
            
        Returns:
            Corps du message en texte
        """
        body = ''
        
        try:
            if 'parts' in payload:
                # Email multipart
                for part in payload['parts']:
                    mime_type = part.get('mimeType', '')
                    
                    # Préférer le texte brut
                    if mime_type == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                            break
                    
                    # Si pas de texte brut, prendre HTML
                    elif mime_type == 'text/html' and not body:
                        data = part['body'].get('data', '')
                        if data:
                            html_content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                            # Extraire le texte du HTML (simplifié)
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(html_content, 'html.parser')
                            body = soup.get_text(separator='\n', strip=True)
                    
                    # Gérer les parties imbriquées
                    elif 'parts' in part:
                        nested_body = self._get_message_body(part)
                        if nested_body:
                            body = nested_body
                            break
            
            elif 'body' in payload:
                # Email simple
                data = payload['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            
            return body.strip()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction du corps du message: {e}")
            return ''
    
    def get_current_history_id(self):
        """
        Récupère l'ID d'historique actuel pour les syncs futures
        
        Returns:
            History ID actuel
        """
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile.get('historyId')
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'history ID: {e}")
            return None
    
    def get_user_email(self):
        """
        Récupère l'adresse email de l'utilisateur connecté
        
        Returns:
            Adresse email
        """
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress')
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'email utilisateur: {e}")
            return None
    
    def test_connection(self):
        """
        Teste la connexion à Gmail
        
        Returns:
            True si la connexion est OK, False sinon
        """
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            logger.info(f"Connexion Gmail OK pour {profile.get('emailAddress')}")
            return True
        except Exception as e:
            logger.error(f"Échec du test de connexion Gmail: {e}")
            return False
