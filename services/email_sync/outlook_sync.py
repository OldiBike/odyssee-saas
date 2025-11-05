"""
Outlook Email Sync Service - Phase 3C
Synchronisation des emails via Microsoft Graph API
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import msal
import requests
from models import Agency
from utils.crypto import decrypt_api_key

logger = logging.getLogger(__name__)


class OutlookSync:
    """Service de synchronisation pour Outlook/Microsoft 365"""
    
    # Scopes nécessaires pour Microsoft Graph
    SCOPES = [
        'https://graph.microsoft.com/Mail.Read',
        'https://graph.microsoft.com/Mail.Send',
        'https://graph.microsoft.com/User.Read'
    ]
    
    GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
    
    def __init__(self, agency: Agency, client_id: str, client_secret: str, tenant_id: str = 'common'):
        """
        Initialise le service Outlook Sync.
        
        Args:
            agency: Instance de l'agence
            client_id: ID de l'application Microsoft
            client_secret: Secret de l'application Microsoft
            tenant_id: ID du tenant (par défaut: 'common' pour multi-tenant)
        """
        self.agency = agency
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        
        # Initialiser MSAL
        self.msal_app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=f'https://login.microsoftonline.com/{tenant_id}'
        )
    
    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """
        Génère l'URL d'autorisation OAuth2.
        
        Args:
            redirect_uri: URI de redirection après l'autorisation
            state: État pour la sécurité CSRF
            
        Returns:
            str: URL d'autorisation
        """
        auth_url = self.msal_app.get_authorization_request_url(
            scopes=self.SCOPES,
            redirect_uri=redirect_uri,
            state=state
        )
        return auth_url
    
    def get_tokens_from_code(self, code: str, redirect_uri: str) -> Optional[Dict]:
        """
        Échange le code d'autorisation contre des tokens d'accès.
        
        Args:
            code: Code d'autorisation reçu
            redirect_uri: URI de redirection
            
        Returns:
            dict: Tokens (access_token, refresh_token, expires_in)
        """
        try:
            result = self.msal_app.acquire_token_by_authorization_code(
                code=code,
                scopes=self.SCOPES,
                redirect_uri=redirect_uri
            )
            
            if 'access_token' in result:
                return {
                    'access_token': result['access_token'],
                    'refresh_token': result.get('refresh_token'),
                    'expires_in': result.get('expires_in', 3600),
                    'id_token': result.get('id_token')
                }
            else:
                error = result.get('error', 'Unknown error')
                error_desc = result.get('error_description', '')
                logger.error(f"Error acquiring token: {error} - {error_desc}")
                return None
                
        except Exception as e:
            logger.error(f"Exception getting tokens from code: {str(e)}", exc_info=True)
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        """
        Rafraîchit le token d'accès.
        
        Args:
            refresh_token: Token de rafraîchissement
            
        Returns:
            dict: Nouveaux tokens
        """
        try:
            result = self.msal_app.acquire_token_by_refresh_token(
                refresh_token=refresh_token,
                scopes=self.SCOPES
            )
            
            if 'access_token' in result:
                return {
                    'access_token': result['access_token'],
                    'refresh_token': result.get('refresh_token', refresh_token),
                    'expires_in': result.get('expires_in', 3600)
                }
            else:
                logger.error(f"Error refreshing token: {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"Exception refreshing token: {str(e)}", exc_info=True)
            return None
    
    def get_access_token(self) -> Optional[str]:
        """
        Récupère un token d'accès valide (rafraîchit si nécessaire).
        
        Returns:
            str: Token d'accès ou None
        """
        try:
            # Vérifier si le token actuel est encore valide
            if self.agency.email_token_expiry:
                if datetime.utcnow() < self.agency.email_token_expiry - timedelta(minutes=5):
                    # Token encore valide (avec marge de 5 minutes)
                    return decrypt_value(self.agency.email_access_token_encrypted)
            
            # Token expiré ou inexistant, rafraîchir
            if self.agency.email_refresh_token_encrypted:
                refresh_token = decrypt_value(self.agency.email_refresh_token_encrypted)
                new_tokens = self.refresh_access_token(refresh_token)
                
                if new_tokens:
                    return new_tokens['access_token']
            
            logger.error("No valid token available and cannot refresh")
            return None
            
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}", exc_info=True)
            return None
    
    def get_user_info(self, access_token: str) -> Optional[Dict]:
        """
        Récupère les informations de l'utilisateur.
        
        Args:
            access_token: Token d'accès
            
        Returns:
            dict: Informations utilisateur
        """
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                f'{self.GRAPH_API_ENDPOINT}/me',
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting user info: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception getting user info: {str(e)}", exc_info=True)
            return None
    
    def fetch_emails(self, max_results: int = 100, since_date: Optional[datetime] = None) -> List[Dict]:
        """
        Récupère les emails depuis Outlook.
        
        Args:
            max_results: Nombre maximum d'emails à récupérer
            since_date: Date à partir de laquelle récupérer les emails
            
        Returns:
            list: Liste des emails
        """
        try:
            access_token = self.get_access_token()
            if not access_token:
                logger.error("No access token available")
                return []
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Construire les paramètres de requête
            params = {
                '$top': min(max_results, 1000),  # Max 1000 par requête
                '$orderby': 'receivedDateTime desc',
                '$select': 'id,subject,from,toRecipients,ccRecipients,receivedDateTime,bodyPreview,body,isRead,conversationId'
            }
            
            # Ajouter le filtre de date si spécifié
            if since_date:
                date_str = since_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                params['$filter'] = f'receivedDateTime gt {date_str}'
            
            # Effectuer la requête
            response = requests.get(
                f'{self.GRAPH_API_ENDPOINT}/me/messages',
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                emails = data.get('value', [])
                
                # Formater les emails
                formatted_emails = []
                for email in emails:
                    formatted_emails.append(self._format_email(email))
                
                logger.info(f"Fetched {len(formatted_emails)} emails from Outlook")
                return formatted_emails
            else:
                logger.error(f"Error fetching emails: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Exception fetching emails: {str(e)}", exc_info=True)
            return []
    
    def _format_email(self, email: Dict) -> Dict:
        """
        Formate un email Outlook au format standard.
        
        Args:
            email: Email brut de Microsoft Graph
            
        Returns:
            dict: Email formaté
        """
        try:
            # Extraire l'expéditeur
            from_address = ''
            from_name = ''
            if email.get('from') and email['from'].get('emailAddress'):
                from_address = email['from']['emailAddress'].get('address', '')
                from_name = email['from']['emailAddress'].get('name', '')
            
            # Extraire les destinataires
            to_addresses = []
            for recipient in email.get('toRecipients', []):
                if recipient.get('emailAddress'):
                    to_addresses.append(recipient['emailAddress'].get('address', ''))
            
            # Extraire les CC
            cc_addresses = []
            for recipient in email.get('ccRecipients', []):
                if recipient.get('emailAddress'):
                    cc_addresses.append(recipient['emailAddress'].get('address', ''))
            
            # Extraire le contenu
            body_content = ''
            if email.get('body'):
                body_content = email['body'].get('content', '')
            
            # Date de réception
            received_date = None
            if email.get('receivedDateTime'):
                try:
                    received_date = datetime.strptime(
                        email['receivedDateTime'][:19], 
                        '%Y-%m-%dT%H:%M:%S'
                    )
                except:
                    pass
            
            return {
                'id': email.get('id', ''),
                'thread_id': email.get('conversationId', ''),
                'subject': email.get('subject', ''),
                'from': from_address,
                'from_name': from_name,
                'to': ', '.join(to_addresses),
                'cc': ', '.join(cc_addresses),
                'date': received_date,
                'body': body_content,
                'snippet': email.get('bodyPreview', ''),
                'is_read': email.get('isRead', False),
                'provider': 'outlook'
            }
            
        except Exception as e:
            logger.error(f"Error formatting email: {str(e)}", exc_info=True)
            return {}
    
    def send_email(self, to: str, subject: str, body: str, 
                   cc: Optional[str] = None, attachments: Optional[List] = None) -> bool:
        """
        Envoie un email via Outlook.
        
        Args:
            to: Destinataire
            subject: Sujet
            body: Corps de l'email (HTML)
            cc: CC (optionnel)
            attachments: Pièces jointes (optionnel)
            
        Returns:
            bool: True si envoyé avec succès
        """
        try:
            access_token = self.get_access_token()
            if not access_token:
                logger.error("No access token available")
                return False
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Construire le message
            message = {
                'subject': subject,
                'body': {
                    'contentType': 'HTML',
                    'content': body
                },
                'toRecipients': [
                    {
                        'emailAddress': {
                            'address': to
                        }
                    }
                ]
            }
            
            # Ajouter CC si présent
            if cc:
                message['ccRecipients'] = [
                    {
                        'emailAddress': {
                            'address': cc
                        }
                    }
                ]
            
            # TODO: Ajouter support des pièces jointes
            
            # Envoyer l'email
            response = requests.post(
                f'{self.GRAPH_API_ENDPOINT}/me/sendMail',
                headers=headers,
                json={'message': message}
            )
            
            if response.status_code == 202:  # Accepted
                logger.info(f"Email sent successfully to {to}")
                return True
            else:
                logger.error(f"Error sending email: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Exception sending email: {str(e)}", exc_info=True)
            return False
