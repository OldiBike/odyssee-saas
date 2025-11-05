"""
Service de parsing et de matching des emails
Gère l'extraction des adresses email et le matching avec les clients
"""

import re
from models import Client
from sqlalchemy import or_
import logging

logger = logging.getLogger(__name__)


class EmailParser:
    """Classe utilitaire pour parser les emails"""
    
    @staticmethod
    def extract_email_address(email_string):
        """
        Extrait l'adresse email pure d'une chaîne comme "John Doe <john@example.com>"
        
        Args:
            email_string: Chaîne contenant un email
            
        Returns:
            Adresse email pure
        """
        if not email_string:
            return None
        
        email_string = email_string.strip()
        
        # Si l'email est au format "Name <email@domain.com>"
        if '<' in email_string and '>' in email_string:
            match = re.search(r'<([^>]+)>', email_string)
            if match:
                return match.group(1).lower().strip()
        
        # Sinon, vérifier si c'est déjà un email valide
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, email_string):
            return email_string.lower().strip()
        
        # Essayer d'extraire un email de la chaîne
        match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email_string)
        if match:
            return match.group(0).lower().strip()
        
        return None
    
    @staticmethod
    def extract_all_emails(email_string):
        """
        Extrait toutes les adresses email d'une chaîne
        
        Args:
            email_string: Chaîne contenant potentiellement plusieurs emails
            
        Returns:
            Liste d'adresses email
        """
        if not email_string:
            return []
        
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, email_string)
        return [email.lower().strip() for email in emails]
    
    @staticmethod
    def clean_email_body(body, max_length=5000):
        """
        Nettoie le corps de l'email en supprimant les éléments inutiles
        
        Args:
            body: Corps de l'email
            max_length: Longueur maximale à garder
            
        Returns:
            Corps nettoyé
        """
        if not body:
            return ''
        
        # Supprimer les lignes de signature communes
        lines = body.split('\n')
        cleaned_lines = []
        
        signature_markers = [
            '-- ',
            'Envoyé depuis',
            'Sent from',
            'Get Outlook',
            'Cordialement',
            'Bien cordialement',
            'Best regards',
            'Kind regards',
        ]
        
        in_signature = False
        for line in lines:
            # Détecter le début d'une signature
            if any(marker in line for marker in signature_markers):
                in_signature = True
                continue
            
            if not in_signature:
                cleaned_lines.append(line)
        
        cleaned_body = '\n'.join(cleaned_lines).strip()
        
        # Limiter la longueur
        if len(cleaned_body) > max_length:
            cleaned_body = cleaned_body[:max_length] + '...'
        
        return cleaned_body


class EmailMatcher:
    """Classe pour matcher les emails avec les clients existants"""
    
    @staticmethod
    def find_client_from_email(email_address, agency_id):
        """
        Trouve un client à partir d'une adresse email
        
        Args:
            email_address: Adresse email à rechercher
            agency_id: ID de l'agence
            
        Returns:
            Client trouvé ou None
        """
        if not email_address:
            return None
        
        # Nettoyer l'adresse email
        clean_email = EmailParser.extract_email_address(email_address)
        if not clean_email:
            return None
        
        # Chercher un client avec cet email
        try:
            client = Client.query.filter_by(
                agency_id=agency_id,
                email=clean_email
            ).first()
            
            if client:
                logger.info(f"Client trouvé: {client.first_name} {client.last_name} pour {clean_email}")
            else:
                logger.debug(f"Aucun client trouvé pour {clean_email}")
            
            return client
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche du client: {e}")
            return None
    
    @staticmethod
    def find_clients_from_email_list(email_list, agency_id):
        """
        Trouve tous les clients correspondant à une liste d'emails
        
        Args:
            email_list: Liste d'adresses email (str séparées par virgules ou liste)
            agency_id: ID de l'agence
            
        Returns:
            Liste de clients trouvés
        """
        if not email_list:
            return []
        
        # Convertir en liste si c'est une chaîne
        if isinstance(email_list, str):
            emails = EmailParser.extract_all_emails(email_list)
        else:
            emails = email_list
        
        clients = []
        for email in emails:
            client = EmailMatcher.find_client_from_email(email, agency_id)
            if client and client not in clients:
                clients.append(client)
        
        return clients
    
    @staticmethod
    def determine_client_from_email(email_data, agency_id, agency_email):
        """
        Détermine le client concerné par un email (expéditeur ou destinataire)
        
        Args:
            email_data: Dict contenant 'from', 'to', 'cc', 'is_sent'
            agency_id: ID de l'agence
            agency_email: Email de l'agence pour identifier les emails sortants
            
        Returns:
            Client trouvé ou None
        """
        email_from = email_data.get('from', '')
        email_to = email_data.get('to', '')
        email_cc = email_data.get('cc', '')
        is_sent = email_data.get('is_sent', False)
        
        # Si l'email a été envoyé par l'agence, chercher le client parmi les destinataires
        if is_sent or (agency_email and EmailParser.extract_email_address(email_from) == agency_email.lower()):
            # Chercher dans les destinataires
            all_recipients = f"{email_to}, {email_cc}"
            clients = EmailMatcher.find_clients_from_email_list(all_recipients, agency_id)
            
            if clients:
                # Retourner le premier client trouvé
                # TODO: Gérer le cas où il y a plusieurs clients
                return clients[0]
        else:
            # Email reçu: le client est l'expéditeur
            client = EmailMatcher.find_client_from_email(email_from, agency_id)
            if client:
                return client
        
        return None
    
    @staticmethod
    def is_relevant_email(email_data, agency_email):
        """
        Détermine si un email est pertinent pour le CRM
        (implique l'agence en tant qu'expéditeur ou destinataire)
        
        Args:
            email_data: Dict contenant les données de l'email
            agency_email: Email de l'agence
            
        Returns:
            True si pertinent, False sinon
        """
        if not agency_email:
            return True  # Par défaut, considérer comme pertinent
        
        agency_email = agency_email.lower() if agency_email else None
        
        email_from = EmailParser.extract_email_address(email_data.get('from', ''))
        email_to_list = EmailParser.extract_all_emails(email_data.get('to', ''))
        email_cc_list = EmailParser.extract_all_emails(email_data.get('cc', ''))
        
        # Vérifier si l'agence est impliquée
        all_emails = [email_from] + email_to_list + email_cc_list
        all_emails = [e for e in all_emails if e]  # Supprimer les None
        
        return agency_email in all_emails
