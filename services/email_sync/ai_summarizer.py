"""
Service de résumé IA pour les emails
Utilise Gemini pour générer des résumés intelligents
"""

import google.generativeai as genai
import os
import logging
from utils.crypto import decrypt_api_key

logger = logging.getLogger(__name__)


class EmailSummarizer:
    """Service pour générer des résumés IA des emails avec Gemini"""
    
    def __init__(self, api_key=None, agency=None):
        """
        Initialise le service de résumé
        
        Args:
            api_key: Clé API Gemini (optionnel)
            agency: Objet Agency pour récupérer la clé depuis la base de données
        """
        # Essayer de récupérer la clé depuis l'agence d'abord
        if agency and hasattr(agency, 'google_api_key_encrypted') and agency.google_api_key_encrypted:
            try:
                self.api_key = decrypt_api_key(agency.google_api_key_encrypted)
                logger.info("Clé API Gemini récupérée depuis l'agence")
            except Exception as e:
                logger.error(f"Erreur lors du déchiffrement de la clé Gemini: {e}")
                self.api_key = None
        else:
            # Sinon, utiliser la clé fournie ou celle de l'environnement
            self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            logger.warning("Aucune clé API Gemini fournie")
            self.model = None
            return
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Service de résumé IA initialisé avec gemini-1.5-flash")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de Gemini: {e}")
            self.model = None
    
    def summarize_email(self, email_subject, email_body, max_summary_length=200):
        """
        Génère un résumé concis de l'email
        
        Args:
            email_subject: Sujet de l'email
            email_body: Corps de l'email
            max_summary_length: Longueur maximale du résumé en caractères
            
        Returns:
            Résumé généré ou None si erreur
        """
        if not self.model:
            logger.warning("Service de résumé IA non disponible")
            return None
        
        # Limiter la longueur du corps pour éviter les tokens excessifs
        truncated_body = email_body[:2000] if len(email_body) > 2000 else email_body
        
        prompt = f"""Résume cet email en 2-3 phrases courtes et précises (maximum {max_summary_length} caractères).
Focus sur les points clés et actions demandées.
Sois concis et professionnel.

Sujet: {email_subject}

Contenu:
{truncated_body}

Résumé:"""
        
        try:
            response = self.model.generate_content(prompt)
            summary = response.text.strip()
            
            # Limiter la longueur du résumé
            if len(summary) > max_summary_length:
                summary = summary[:max_summary_length-3] + '...'
            
            logger.info(f"Résumé généré: {summary[:50]}...")
            return summary
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du résumé: {e}")
            return None
    
    def detect_sentiment(self, email_body):
        """
        Détecte le sentiment de l'email (positif/négatif/neutre)
        
        Args:
            email_body: Corps de l'email
            
        Returns:
            'positif', 'négatif' ou 'neutre'
        """
        if not self.model:
            return 'neutre'
        
        truncated_body = email_body[:1000] if len(email_body) > 1000 else email_body
        
        prompt = f"""Analyse le sentiment de cet email.
Réponds UNIQUEMENT par un seul mot: "positif", "négatif" ou "neutre"

Email:
{truncated_body}

Sentiment:"""
        
        try:
            response = self.model.generate_content(prompt)
            sentiment = response.text.strip().lower()
            
            # Valider la réponse
            if sentiment in ['positif', 'négatif', 'neutre']:
                return sentiment
            
            # Si la réponse n'est pas valide, essayer de la détecter
            if 'positif' in sentiment:
                return 'positif'
            elif 'négatif' in sentiment or 'négatif' in sentiment:
                return 'négatif'
            else:
                return 'neutre'
                
        except Exception as e:
            logger.error(f"Erreur lors de la détection du sentiment: {e}")
            return 'neutre'
    
    def extract_key_points(self, email_body):
        """
        Extrait les points clés d'un email
        
        Args:
            email_body: Corps de l'email
            
        Returns:
            Liste de points clés ou None
        """
        if not self.model:
            return None
        
        truncated_body = email_body[:2000] if len(email_body) > 2000 else email_body
        
        prompt = f"""Extrais les 3-5 points clés de cet email sous forme de liste à puces.
Sois concis et factuel.

Email:
{truncated_body}

Points clés:"""
        
        try:
            response = self.model.generate_content(prompt)
            key_points = response.text.strip()
            
            logger.info("Points clés extraits avec succès")
            return key_points
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des points clés: {e}")
            return None
    
    def detect_action_required(self, email_subject, email_body):
        """
        Détecte si l'email nécessite une action
        
        Args:
            email_subject: Sujet de l'email
            email_body: Corps de l'email
            
        Returns:
            Dict avec 'required' (bool) et 'action' (str) ou None
        """
        if not self.model:
            return None
        
        truncated_body = email_body[:1500] if len(email_body) > 1500 else email_body
        
        prompt = f"""Analyse cet email et détermine s'il nécessite une action.
Réponds au format JSON:
{{"required": true/false, "action": "description courte de l'action si required=true, sinon null"}}

Sujet: {email_subject}

Email:
{truncated_body}

Analyse:"""
        
        try:
            response = self.model.generate_content(prompt)
            result = response.text.strip()
            
            # Essayer de parser le JSON
            import json
            try:
                data = json.loads(result)
                return data
            except:
                # Si pas de JSON valide, essayer de déterminer manuellement
                if 'true' in result.lower() or 'action' in result.lower():
                    return {'required': True, 'action': 'Action à déterminer'}
                else:
                    return {'required': False, 'action': None}
                    
        except Exception as e:
            logger.error(f"Erreur lors de la détection d'action: {e}")
            return None
    
    def categorize_email(self, email_subject, email_body):
        """
        Catégorise l'email (demande, information, réclamation, etc.)
        
        Args:
            email_subject: Sujet de l'email
            email_body: Corps de l'email
            
        Returns:
            Catégorie de l'email
        """
        if not self.model:
            return 'autre'
        
        truncated_body = email_body[:1000] if len(email_body) > 1000 else email_body
        
        prompt = f"""Catégorise cet email en UN seul mot parmi:
- demande_devis
- demande_information
- reclamation
- confirmation
- remerciement
- relance
- autre

Sujet: {email_subject}

Email:
{truncated_body}

Catégorie:"""
        
        try:
            response = self.model.generate_content(prompt)
            category = response.text.strip().lower()
            
            valid_categories = [
                'demande_devis', 'demande_information', 'reclamation',
                'confirmation', 'remerciement', 'relance', 'autre'
            ]
            
            # Chercher une catégorie valide dans la réponse
            for cat in valid_categories:
                if cat in category:
                    return cat
            
            return 'autre'
            
        except Exception as e:
            logger.error(f"Erreur lors de la catégorisation: {e}")
            return 'autre'
