"""
Service d'envoi d'emails via Gmail et Outlook
Gère l'envoi d'emails et les réponses avec threading
"""

import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from datetime import datetime
import json
from typing import Optional, Dict, Any
import requests
import smtplib
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models import Agency, ClientInteraction, db


class EmailSendError(Exception):
    """Exception levée quand l'envoi d'email échoue"""
    pass


class EmailSender:
    """Service pour envoyer des emails via Gmail ou Outlook"""
    
    def __init__(self, agency_id: int):
        """
        Initialise le service d'envoi pour une agence
        
        Args:
            agency_id: ID de l'agence
            
        Raises:
            EmailSendError: Si l'agence n'est pas configurée pour l'envoi d'emails
        """
        self.agency = Agency.query.get(agency_id)
        if not self.agency:
            raise EmailSendError(f"Agency {agency_id} not found")
        
        self.agency_id = agency_id
        
        # Déterminer le type de configuration
        self.config_type = self.agency.email_config_type or 'oauth'
        
        if self.config_type == 'oauth':
            # Configuration OAuth existante (Gmail/Outlook)
            if not self.agency.email_sync_enabled:
                raise EmailSendError("Email sync not enabled for this agency")
            
            if not self.agency.email_sync_provider:
                raise EmailSendError("No email provider configured")
            
            self.provider = self.agency.email_sync_provider
            
        elif self.config_type == 'manual':
            # Configuration SMTP/IMAP manuelle
            self.provider = 'manual'
            self.smtp_config = self._load_smtp_config()
            self.imap_config = self._load_imap_config()
            
            if not self.smtp_config or not self.imap_config:
                raise EmailSendError("SMTP/IMAP config not found")
        else:
            raise EmailSendError(f"Unknown config type: {self.config_type}")
        
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to_message_id: Optional[str] = None,
        reply_to_thread_id: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envoie un email via le provider configuré
        
        Args:
            to: Adresse email destinataire
            subject: Sujet de l'email
            body: Corps de l'email (texte brut)
            reply_to_message_id: ID du message auquel on répond (optionnel)
            reply_to_thread_id: ID du thread Gmail (optionnel)
            cc: Adresses en copie (optionnel)
            bcc: Adresses en copie cachée (optionnel)
            html_body: Corps HTML de l'email (optionnel)
            
        Returns:
            Dict avec les informations de l'email envoyé
            {
                'success': bool,
                'message_id': str,
                'thread_id': str (pour Gmail),
                'sent_at': datetime,
                'error': str (si erreur)
            }
            
        Raises:
            EmailSendError: Si l'envoi échoue
        """
        if self.provider == 'gmail':
            return self._send_via_gmail(
                to, subject, body, reply_to_message_id, 
                reply_to_thread_id, cc, bcc, html_body
            )
        elif self.provider == 'outlook':
            return self._send_via_outlook(
                to, subject, body, reply_to_message_id,
                cc, bcc, html_body
            )
        elif self.provider == 'manual':
            return self._send_via_smtp(
                to, subject, body, reply_to_message_id,
                cc, bcc, html_body
            )
        else:
            raise EmailSendError(f"Unsupported provider: {self.provider}")
    
    def _load_smtp_config(self) -> Optional[Dict[str, Any]]:
        """Charge et déchiffre la configuration SMTP"""
        from utils.crypto import decrypt_config
        
        if not self.agency.smtp_config_encrypted:
            return None
        
        try:
            config = decrypt_config(self.agency.smtp_config_encrypted)
            
            # Validation
            required_fields = ['host', 'port', 'username', 'password', 'from_email']
            if not all(field in config for field in required_fields):
                raise EmailSendError("Invalid SMTP config: missing required fields")
            
            return config
        except Exception as e:
            raise EmailSendError(f"Failed to load SMTP config: {str(e)}")
    
    def _load_imap_config(self) -> Optional[Dict[str, Any]]:
        """Charge et déchiffre la configuration IMAP"""
        from utils.crypto import decrypt_config
        
        if not self.agency.imap_config_encrypted:
            return None
        
        try:
            config = decrypt_config(self.agency.imap_config_encrypted)
            
            # Validation
            required_fields = ['host', 'port', 'username', 'password']
            if not all(field in config for field in required_fields):
                raise EmailSendError("Invalid IMAP config: missing required fields")
            
            return config
        except Exception as e:
            raise EmailSendError(f"Failed to load IMAP config: {str(e)}")
    
    def _send_via_gmail(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to_message_id: Optional[str] = None,
        reply_to_thread_id: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """Envoie un email via Gmail API"""
        try:
            # Créer les credentials
            creds = Credentials(
                token=self.agency.email_oauth_access_token,
                refresh_token=self.agency.email_oauth_refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=self.agency.email_oauth_client_id,
                client_secret=self.agency.email_oauth_client_secret
            )
            
            # Build Gmail service
            service = build('gmail', 'v1', credentials=creds)
            
            # Créer le message
            if html_body:
                message = MIMEMultipart('alternative')
                part1 = MIMEText(body, 'plain')
                part2 = MIMEText(html_body, 'html')
                message.attach(part1)
                message.attach(part2)
            else:
                message = MIMEText(body)
            
            message['to'] = to
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Si c'est une réponse, ajouter les headers appropriés
            if reply_to_message_id:
                message['In-Reply-To'] = reply_to_message_id
                message['References'] = reply_to_message_id
            
            # Encoder le message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Préparer le body de la requête
            send_body = {'raw': raw_message}
            
            # Si c'est une réponse dans un thread, inclure le threadId
            if reply_to_thread_id:
                send_body['threadId'] = reply_to_thread_id
            
            # Envoyer
            sent_message = service.users().messages().send(
                userId='me',
                body=send_body
            ).execute()
            
            # Enregistrer l'interaction dans la base
            self._save_sent_email(
                message_id=sent_message['id'],
                thread_id=sent_message.get('threadId'),
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc
            )
            
            return {
                'success': True,
                'message_id': sent_message['id'],
                'thread_id': sent_message.get('threadId'),
                'sent_at': datetime.utcnow(),
                'provider': 'gmail'
            }
            
        except HttpError as error:
            error_details = error.error_details if hasattr(error, 'error_details') else str(error)
            raise EmailSendError(f"Gmail API error: {error_details}")
        except Exception as e:
            raise EmailSendError(f"Failed to send email via Gmail: {str(e)}")
    
    def _send_via_outlook(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to_message_id: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """Envoie un email via Microsoft Graph API"""
        try:
            # Préparer le message
            message_data = {
                'subject': subject,
                'body': {
                    'contentType': 'HTML' if html_body else 'Text',
                    'content': html_body if html_body else body
                },
                'toRecipients': [
                    {'emailAddress': {'address': to}}
                ]
            }
            
            if cc:
                cc_list = [addr.strip() for addr in cc.split(',')]
                message_data['ccRecipients'] = [
                    {'emailAddress': {'address': addr}} for addr in cc_list
                ]
            
            if bcc:
                bcc_list = [addr.strip() for addr in bcc.split(',')]
                message_data['bccRecipients'] = [
                    {'emailAddress': {'address': addr}} for addr in bcc_list
                ]
            
            # Headers pour l'API
            headers = {
                'Authorization': f'Bearer {self.agency.email_oauth_access_token}',
                'Content-Type': 'application/json'
            }
            
            # Si c'est une réponse, utiliser l'endpoint reply
            if reply_to_message_id:
                url = f'https://graph.microsoft.com/v1.0/me/messages/{reply_to_message_id}/reply'
                payload = {
                    'message': message_data,
                    'comment': body
                }
            else:
                # Sinon, créer un nouveau message
                url = 'https://graph.microsoft.com/v1.0/me/sendMail'
                payload = {'message': message_data}
            
            # Envoyer
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code not in [200, 201, 202]:
                error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                raise EmailSendError(f"Outlook API error: {error_msg}")
            
            # Pour Outlook, l'email envoyé n'a pas forcément un ID retourné immédiatement
            # On peut chercher dans les emails envoyés ou utiliser un ID temporaire
            message_id = response.json().get('id', f"outlook-{datetime.utcnow().timestamp()}")
            
            # Enregistrer l'interaction
            self._save_sent_email(
                message_id=message_id,
                thread_id=None,  # Outlook gère différemment les threads
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc
            )
            
            return {
                'success': True,
                'message_id': message_id,
                'thread_id': None,
                'sent_at': datetime.utcnow(),
                'provider': 'outlook'
            }
            
        except requests.exceptions.RequestException as e:
            raise EmailSendError(f"Outlook API request failed: {str(e)}")
        except Exception as e:
            raise EmailSendError(f"Failed to send email via Outlook: {str(e)}")
    
    def _send_via_smtp(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to_message_id: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """Envoie un email via SMTP"""
        try:
            # Créer le message
            if html_body:
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
                msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            else:
                msg = MIMEText(body, 'plain', 'utf-8')
            
            msg['From'] = self.smtp_config['from_email']
            msg['To'] = to
            msg['Subject'] = subject
            msg['Date'] = formatdate(localtime=True)
            msg['Message-ID'] = make_msgid()
            
            # Threading
            if reply_to_message_id:
                msg['In-Reply-To'] = reply_to_message_id
                msg['References'] = reply_to_message_id
            
            # CC et BCC
            if cc:
                msg['Cc'] = cc
            if bcc:
                msg['Bcc'] = bcc
            
            # Connexion SMTP
            use_ssl = self.smtp_config.get('use_ssl', True)
            
            if use_ssl:
                server = smtplib.SMTP_SSL(
                    self.smtp_config['host'],
                    int(self.smtp_config['port']),
                    timeout=30
                )
            else:
                server = smtplib.SMTP(
                    self.smtp_config['host'],
                    int(self.smtp_config['port']),
                    timeout=30
                )
                if self.smtp_config.get('use_tls', False):
                    server.starttls()
            
            # Authentification
            server.login(
                self.smtp_config['username'],
                self.smtp_config['password']
            )
            
            # Préparer la liste des destinataires
            recipients = [to]
            if cc:
                recipients.extend([addr.strip() for addr in cc.split(',')])
            if bcc:
                recipients.extend([addr.strip() for addr in bcc.split(',')])
            
            # Envoi
            server.send_message(msg, to_addrs=recipients)
            server.quit()
            
            # Sauvegarder dans la base de données
            self._save_sent_email(
                message_id=msg['Message-ID'],
                thread_id=reply_to_message_id or msg['Message-ID'],
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc
            )
            
            return {
                'success': True,
                'message_id': msg['Message-ID'],
                'thread_id': reply_to_message_id or msg['Message-ID'],
                'sent_at': datetime.utcnow(),
                'provider': 'manual'
            }
            
        except smtplib.SMTPAuthenticationError as e:
            raise EmailSendError(f"SMTP authentication error: {str(e)}")
        except smtplib.SMTPException as e:
            raise EmailSendError(f"SMTP error: {str(e)}")
        except Exception as e:
            raise EmailSendError(f"Email send error: {str(e)}")
    
    def _save_sent_email(
        self,
        message_id: str,
        thread_id: Optional[str],
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ):
        """
        Enregistre l'email envoyé dans la base de données
        
        Args:
            message_id: ID du message
            thread_id: ID du thread (Gmail)
            to: Destinataire
            subject: Sujet
            body: Corps du message
            cc: Copie (optionnel)
            bcc: Copie cachée (optionnel)
        """
        try:
            # Essayer de trouver le client associé
            from models import Client, User
            client = Client.query.filter_by(
                agency_id=self.agency_id,
                email=to.strip()
            ).first()
            
            # Si pas de client trouvé, on ne peut pas créer l'interaction
            # car client_id est requis et user_id aussi
            if not client:
                print(f"Warning: No client found for email {to}, skipping interaction save")
                return
            
            # Trouver un utilisateur de l'agence pour créer l'interaction
            user = User.query.filter_by(
                agency_id=self.agency_id,
                role='agency_admin'
            ).first()
            
            if not user:
                # Fallback sur n'importe quel utilisateur de l'agence
                user = User.query.filter_by(agency_id=self.agency_id).first()
            
            if not user:
                print(f"Warning: No user found for agency {self.agency_id}, skipping interaction save")
                return
            
            # Construire les destinataires
            recipients = to
            if cc:
                recipients += f", {cc}"
            if bcc:
                recipients += f" (bcc: {bcc})"
            
            # Créer l'interaction
            interaction = ClientInteraction(
                client_id=client.id,
                user_id=user.id,
                interaction_type='email',
                is_outbound=True,
                content=body,
                created_at=datetime.utcnow(),
                email_message_id=message_id,
                email_thread_id=thread_id,
                email_subject=subject,
                email_from=self.agency.email_sync_email or self.smtp_config.get('from_email', 'unknown'),
                email_to=recipients,
                ai_summary=f"Email envoyé à {to}: {subject}"
            )
            
            db.session.add(interaction)
            db.session.commit()
            
        except Exception as e:
            # Log l'erreur mais ne pas faire échouer l'envoi
            print(f"Warning: Failed to save sent email to database: {e}")
            db.session.rollback()
    
    def reply_to_email(
        self,
        interaction_id: int,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Répond à un email existant en récupérant les infos depuis la DB
        
        Args:
            interaction_id: ID de l'interaction (email) à laquelle répondre
            body: Corps de la réponse
            html_body: Corps HTML (optionnel)
            cc: Copie (optionnel)
            bcc: Copie cachée (optionnel)
            
        Returns:
            Dict avec les informations de l'email envoyé
            
        Raises:
            EmailSendError: Si l'email original n'existe pas ou l'envoi échoue
        """
        # Récupérer l'interaction originale
        original = ClientInteraction.query.get(interaction_id)
        
        if not original:
            raise EmailSendError(f"Email interaction {interaction_id} not found")
        
        # Vérifier que l'interaction appartient bien à cette agence
        if original.client.agency_id != self.agency_id:
            raise EmailSendError(f"Email interaction {interaction_id} does not belong to this agency")
        
        # Vérifier que c'est bien un email
        if original.interaction_type != 'email':
            raise EmailSendError(f"Interaction {interaction_id} is not an email")
        
        # Déterminer le destinataire
        # Si l'email original était reçu (is_outbound=False), répondre à l'expéditeur (email_from)
        # Si l'email original était envoyé (is_outbound=True), répondre au destinataire (email_to)
        if original.is_outbound:
            # On avait envoyé cet email, donc on répond au destinataire original
            to = original.email_to
        else:
            # On avait reçu cet email, donc on répond à l'expéditeur
            to = original.email_from
        
        # Créer le sujet (ajouter Re: si pas déjà présent)
        subject = original.email_subject or "No Subject"
        if not subject.lower().startswith('re:'):
            subject = f"Re: {subject}"
        
        # Envoyer la réponse
        return self.send_email(
            to=to,
            subject=subject,
            body=body,
            reply_to_message_id=original.email_message_id,
            reply_to_thread_id=original.email_thread_id,
            cc=cc,
            bcc=bcc,
            html_body=html_body
        )
    
    @staticmethod
    def get_agency_email_address(agency_id: int) -> Optional[str]:
        """
        Récupère l'adresse email configurée pour une agence
        
        Args:
            agency_id: ID de l'agence
            
        Returns:
            L'adresse email ou None si non configurée
        """
        agency = Agency.query.get(agency_id)
        if agency and agency.email_sync_enabled:
            return agency.email_sync_email
        return None
    
    @staticmethod
    def is_email_send_enabled(agency_id: int) -> bool:
        """
        Vérifie si l'envoi d'emails est activé pour une agence
        
        Args:
            agency_id: ID de l'agence
            
        Returns:
            True si l'envoi est possible, False sinon
        """
        agency = Agency.query.get(agency_id)
        if not agency:
            return False
        
        return (
            agency.email_sync_enabled and
            agency.email_sync_provider in ['gmail', 'outlook'] and
            agency.email_oauth_access_token and
            agency.email_sync_email
        )
