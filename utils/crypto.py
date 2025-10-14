# utils/crypto.py - Système de Chiffrement des Configurations Agences
"""
Ce module gère le chiffrement/déchiffrement des données sensibles des agences.
IMPORTANT: La clé maître (MASTER_ENCRYPTION_KEY) doit TOUJOURS rester la même,
sinon toutes les données chiffrées seront perdues.
"""

from cryptography.fernet import Fernet
import base64
import hashlib
import json
from typing import Optional, Dict, Any


class CryptoManager:
    """
    Gestionnaire de chiffrement pour les données sensibles des agences.
    Utilise Fernet (chiffrement symétrique) de la librairie cryptography.
    """
    
    def __init__(self, master_key: str):
        """
        Initialise le gestionnaire avec une clé maître.
        
        Args:
            master_key: Clé maître (doit être constante en production)
        """
        # Convertir la clé maître en clé Fernet valide (32 bytes URL-safe base64)
        self.fernet = self._create_fernet_from_key(master_key)
    
    def _create_fernet_from_key(self, master_key: str) -> Fernet:
        """
        Convertit une clé maître string en objet Fernet.
        
        La clé doit être de 32 bytes en base64 URL-safe.
        On utilise SHA256 pour dériver une clé de la bonne taille.
        """
        # Dériver une clé de 32 bytes depuis la clé maître
        key_bytes = hashlib.sha256(master_key.encode()).digest()
        # Encoder en base64 URL-safe (format requis par Fernet)
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        return Fernet(fernet_key)
    
    def encrypt(self, data: str) -> str:
        """
        Chiffre une chaîne de caractères.
        
        Args:
            data: Données à chiffrer (string)
            
        Returns:
            Données chiffrées (string base64)
        """
        if not data:
            return ''
        
        try:
            encrypted_bytes = self.fernet.encrypt(data.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            print(f"❌ Erreur de chiffrement: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Déchiffre une chaîne de caractères.
        
        Args:
            encrypted_data: Données chiffrées (string base64)
            
        Returns:
            Données déchiffrées (string)
        """
        if not encrypted_data:
            return ''
        
        try:
            decrypted_bytes = self.fernet.decrypt(encrypted_data.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            print(f"❌ Erreur de déchiffrement: {e}")
            # Si le déchiffrement échoue, c'est probablement que la clé a changé
            raise ValueError("Impossible de déchiffrer les données. La clé maître a peut-être changé.")
    
    def encrypt_json(self, data: Dict[Any, Any]) -> str:
        """
        Chiffre un dictionnaire Python (converti en JSON).
        
        Args:
            data: Dictionnaire à chiffrer
            
        Returns:
            JSON chiffré (string)
        """
        json_str = json.dumps(data)
        return self.encrypt(json_str)
    
    def decrypt_json(self, encrypted_json: str) -> Dict[Any, Any]:
        """
        Déchiffre un JSON chiffré et le retourne en dictionnaire.
        
        Args:
            encrypted_json: JSON chiffré (string)
            
        Returns:
            Dictionnaire Python
        """
        json_str = self.decrypt(encrypted_json)
        return json.loads(json_str) if json_str else {}


# ==============================================================================
# FONCTIONS UTILITAIRES GLOBALES
# ==============================================================================

_crypto_manager_instance: Optional[CryptoManager] = None


def init_crypto(master_key: str):
    """
    Initialise le gestionnaire de chiffrement global.
    À appeler au démarrage de l'application.
    
    Args:
        master_key: Clé maître de chiffrement
    """
    global _crypto_manager_instance
    _crypto_manager_instance = CryptoManager(master_key)
    print("🔐 Gestionnaire de chiffrement initialisé")


def get_crypto() -> CryptoManager:
    """
    Retourne l'instance du gestionnaire de chiffrement.
    
    Returns:
        CryptoManager instance
        
    Raises:
        RuntimeError: Si le gestionnaire n'a pas été initialisé
    """
    if _crypto_manager_instance is None:
        raise RuntimeError("❌ Le gestionnaire de chiffrement n'a pas été initialisé. Appelez init_crypto() d'abord.")
    return _crypto_manager_instance


def encrypt_api_key(api_key: str) -> str:
    """
    Raccourci pour chiffrer une clé API.
    
    Args:
        api_key: Clé API en clair
        
    Returns:
        Clé API chiffrée
    """
    return get_crypto().encrypt(api_key)


def decrypt_api_key(encrypted_api_key: str) -> str:
    """
    Raccourci pour déchiffrer une clé API.
    
    Args:
        encrypted_api_key: Clé API chiffrée
        
    Returns:
        Clé API en clair
    """
    return get_crypto().decrypt(encrypted_api_key)


def encrypt_config(config_dict: Dict[str, Any]) -> str:
    """
    Raccourci pour chiffrer un dictionnaire de configuration.
    
    Args:
        config_dict: Configuration (dict)
        
    Returns:
        Configuration chiffrée (string)
    """
    return get_crypto().encrypt_json(config_dict)


def decrypt_config(encrypted_config: str) -> Dict[str, Any]:
    """
    Raccourci pour déchiffrer un dictionnaire de configuration.
    
    Args:
        encrypted_config: Configuration chiffrée (string)
        
    Returns:
        Configuration (dict)
    """
    return get_crypto().decrypt_json(encrypted_config)


# ==============================================================================
# GÉNÉRATION DE CLÉ MAÎTRE
# ==============================================================================

def generate_master_key() -> str:
    """
    Génère une nouvelle clé maître sécurisée.
    
    ⚠️ ATTENTION: À n'utiliser QU'UNE SEULE FOIS lors de la première installation.
    Si vous changez la clé après avoir chiffré des données, elles seront perdues.
    
    Returns:
        Clé maître générée (à sauvegarder dans .env)
    """
    key = Fernet.generate_key()
    return key.decode('utf-8')


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == "__main__":
    """
    Exemple de test du système de chiffrement.
    Lancez ce fichier directement pour tester : python utils/crypto.py
    """
    
    print("\n🔐 TEST DU SYSTÈME DE CHIFFREMENT\n")
    
    # 1) Générer une clé maître
    master_key = generate_master_key()
    print(f"Clé maître générée: {master_key}\n")
    
    # 2) Initialiser le crypto manager
    init_crypto(master_key)
    
    # 3) Tester le chiffrement d'une clé API
    api_key = "sk_test_1234567890abcdef"
    encrypted = encrypt_api_key(api_key)
    decrypted = decrypt_api_key(encrypted)
    
    print(f"Clé API originale : {api_key}")
    print(f"Clé API chiffrée  : {encrypted}")
    print(f"Clé API déchiffrée: {decrypted}")
    print(f"✅ Test réussi: {api_key == decrypted}\n")
    
    # 4) Tester le chiffrement d'une config JSON
    config = {
        "mail_server": "smtp.example.com",
        "mail_port": 587,
        "mail_username": "noreply@example.com",
        "mail_password": "super_secret_password"
    }
    
    encrypted_config = encrypt_config(config)
    decrypted_config = decrypt_config(encrypted_config)
    
    print(f"Config originale : {config}")
    print(f"Config chiffrée  : {encrypted_config[:50]}...")
    print(f"Config déchiffrée: {decrypted_config}")
    print(f"✅ Test réussi: {config == decrypted_config}")