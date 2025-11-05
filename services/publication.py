# services/publication.py
"""
Service de publication des fiches de voyage sur des serveurs externes.
Supporte FTP, FTPS (FTP sécurisé) et SFTP (SSH File Transfer Protocol).
"""

import ftplib
import tempfile
import os
import logging
import requests
from typing import Dict, Optional

# Import optionnel de paramiko pour SFTP
try:
    import paramiko
    SFTP_AVAILABLE = True
except ImportError:
    SFTP_AVAILABLE = False
    logging.warning("Paramiko non installé. Le support SFTP est désactivé.")


def publish_via_ftp(html_content: str, filename: str, ftp_config: Dict[str, str]) -> bool:
    """
    Publie un contenu HTML sur un serveur distant.
    Détecte automatiquement le type de connexion à utiliser (FTP, FTPS, SFTP ou API HTTP).

    Args:
        html_content (str): Le contenu HTML à publier.
        filename (str): Le nom du fichier à créer sur le serveur distant.
        ftp_config (dict): Dictionnaire contenant:
            - 'host': Adresse du serveur (ou URL pour API)
            - 'user': Nom d'utilisateur
            - 'password': Mot de passe (ou clé API)
            - 'path': Chemin distant (optionnel)
            - 'port': Port de connexion (optionnel, 21 pour FTP/FTPS, 22 pour SFTP)
            - 'protocol': Type de connexion ('ftp', 'ftps', 'sftp', 'api', ou 'auto')

    Returns:
        bool: True si la publication a réussi, False sinon.
    """
    protocol = ftp_config.get('protocol', 'auto').lower()
    
    # Publication via API HTTP/HTTPS (pour contourner les blocages d'hébergeurs)
    if protocol == 'api':
        return _publish_api(html_content, filename, ftp_config)
    
    # Publication via FTP/FTPS/SFTP (méthode traditionnelle)
    host = ftp_config.get('host')
    user = ftp_config.get('user')
    password = ftp_config.get('password')
    remote_path = ftp_config.get('path', '/')
    port = ftp_config.get('port')

    if not all([host, user, password]):
        raise ValueError("Configuration incomplète (host, user, password sont requis).")

    # Détection automatique du protocole si nécessaire
    if protocol == 'auto':
        # Si le port est 22, c'est probablement SFTP
        if port == 22 or port == '22':
            protocol = 'sftp'
        # Si le port est 990, c'est probablement FTPS
        elif port == 990 or port == '990':
            protocol = 'ftps'
        # Sinon, utiliser FTP par défaut
        else:
            protocol = 'ftp'

    # Router vers la bonne fonction selon le protocole
    if protocol == 'sftp':
        return _publish_sftp(html_content, filename, host, user, password, remote_path, port or 22)
    elif protocol == 'ftps':
        return _publish_ftps(html_content, filename, host, user, password, remote_path, port or 990)
    else:  # ftp
        return _publish_ftp(html_content, filename, host, user, password, remote_path, port or 21)


def _publish_ftp(html_content: str, filename: str, host: str, user: str, 
                 password: str, remote_path: str, port: int) -> bool:
    """
    Publication via FTP standard (non sécurisé).
    """
    # Créer un fichier temporaire avec le contenu HTML
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.html', encoding='utf-8') as tmp_file:
        tmp_file.write(html_content)
        local_filepath = tmp_file.name

    try:
        # Connexion au serveur FTP
        ftp = ftplib.FTP(timeout=30)
        ftp.connect(host, port)
        ftp.login(user, password)
        
        # Se déplacer vers le bon répertoire
        if remote_path and remote_path != '/':
            try:
                ftp.cwd(remote_path)
            except ftplib.error_perm:
                # Essayer de créer les répertoires manquants
                _create_remote_directories_ftp(ftp, remote_path)
                ftp.cwd(remote_path)

        # Uploader le fichier
        with open(local_filepath, 'rb') as file_to_upload:
            ftp.storbinary(f'STOR {filename}', file_to_upload)
        
        ftp.quit()
        logging.info(f"✅ Fichier '{filename}' publié via FTP sur {host}:{port}{remote_path}")
        return True

    except Exception as e:
        logging.error(f"❌ Erreur de publication FTP: {e}")
        return False
    finally:
        # Supprimer le fichier temporaire
        if os.path.exists(local_filepath):
            os.remove(local_filepath)


def _publish_ftps(html_content: str, filename: str, host: str, user: str, 
                  password: str, remote_path: str, port: int) -> bool:
    """
    Publication via FTPS (FTP over TLS/SSL).
    """
    # Créer un fichier temporaire avec le contenu HTML
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.html', encoding='utf-8') as tmp_file:
        tmp_file.write(html_content)
        local_filepath = tmp_file.name

    try:
        # Connexion au serveur FTPS avec TLS
        ftp = ftplib.FTP_TLS(timeout=30)
        ftp.connect(host, port)
        ftp.login(user, password)
        ftp.prot_p()  # Activer le mode de protection des données
        
        # Se déplacer vers le bon répertoire
        if remote_path and remote_path != '/':
            try:
                ftp.cwd(remote_path)
            except ftplib.error_perm:
                # Essayer de créer les répertoires manquants
                _create_remote_directories_ftp(ftp, remote_path)
                ftp.cwd(remote_path)

        # Uploader le fichier
        with open(local_filepath, 'rb') as file_to_upload:
            ftp.storbinary(f'STOR {filename}', file_to_upload)
        
        ftp.quit()
        logging.info(f"✅ Fichier '{filename}' publié via FTPS sur {host}:{port}{remote_path}")
        return True

    except Exception as e:
        logging.error(f"❌ Erreur de publication FTPS: {e}")
        return False
    finally:
        # Supprimer le fichier temporaire
        if os.path.exists(local_filepath):
            os.remove(local_filepath)


def _publish_sftp(html_content: str, filename: str, host: str, user: str, 
                  password: str, remote_path: str, port: int) -> bool:
    """
    Publication via SFTP (SSH File Transfer Protocol).
    Nécessite la bibliothèque paramiko.
    """
    if not SFTP_AVAILABLE:
        logging.error("❌ Paramiko n'est pas installé. Installez-le avec: pip install paramiko")
        return False

    # Créer un fichier temporaire avec le contenu HTML
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.html', encoding='utf-8') as tmp_file:
        tmp_file.write(html_content)
        local_filepath = tmp_file.name

    try:
        # Créer un client SSH
        transport = paramiko.Transport((host, port))
        transport.connect(username=user, password=password)
        
        # Créer un client SFTP
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # Se déplacer vers le bon répertoire (créer si nécessaire)
        if remote_path and remote_path != '/':
            _create_remote_directories_sftp(sftp, remote_path)
        
        # Construire le chemin complet du fichier distant
        remote_file = os.path.join(remote_path, filename).replace('\\', '/')
        
        # Uploader le fichier
        sftp.put(local_filepath, remote_file)
        
        # Fermer les connexions
        sftp.close()
        transport.close()
        
        logging.info(f"✅ Fichier '{filename}' publié via SFTP sur {host}:{port}{remote_path}")
        return True

    except Exception as e:
        logging.error(f"❌ Erreur de publication SFTP: {e}")
        return False
    finally:
        # Supprimer le fichier temporaire
        if os.path.exists(local_filepath):
            os.remove(local_filepath)


def _create_remote_directories_ftp(ftp: ftplib.FTP, path: str) -> None:
    """
    Crée récursivement les répertoires manquants sur un serveur FTP.
    """
    parts = path.strip('/').split('/')
    current_path = ''
    
    for part in parts:
        current_path += f'/{part}'
        try:
            ftp.cwd(current_path)
        except ftplib.error_perm:
            try:
                ftp.mkd(current_path)
                ftp.cwd(current_path)
            except ftplib.error_perm:
                pass  # Le répertoire existe peut-être déjà


def _create_remote_directories_sftp(sftp: 'paramiko.SFTPClient', path: str) -> None:
    """
    Crée récursivement les répertoires manquants sur un serveur SFTP.
    """
    parts = path.strip('/').split('/')
    current_path = ''
    
    for part in parts:
        current_path += f'/{part}'
        try:
            sftp.stat(current_path)
        except IOError:
            try:
                sftp.mkdir(current_path)
            except IOError:
                pass  # Le répertoire existe peut-être déjà


def _publish_api(html_content: str, filename: str, ftp_config: Dict[str, str]) -> bool:
    """
    Publication via API HTTP/HTTPS personnalisée (upload.php).
    Utilisé pour contourner les blocages d'hébergeurs (ex: Hostinger depuis Railway).
    
    Format compatible avec le fichier upload.php généré par l'application.
    
    Args:
        html_content: Contenu HTML à publier
        filename: Nom du fichier
        ftp_config: Configuration contenant:
            - 'host': URL de l'API (ex: https://www.agence.com/upload.php)
            - 'password': Clé API
            - 'path': Chemin de destination (répertoire, ex: 'voyages')
    
    Returns:
        bool: True si succès, False sinon
    """
    import base64
    
    api_url = ftp_config.get('host')
    api_key = ftp_config.get('password')  # La clé API est stockée dans 'password'
    directory = ftp_config.get('path', 'voyages').strip('/')
    
    if not api_url:
        logging.error("❌ URL de l'API manquante dans la configuration")
        return False
    
    if not api_key:
        logging.error("❌ Clé API manquante dans la configuration")
        return False
    
    try:
        # Encoder le contenu en base64 (format attendu par upload.php)
        content_base64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
        
        # Préparer les données au format attendu par upload.php
        payload = {
            'api_key': api_key,
            'filename': filename,
            'content': content_base64,
            'directory': directory
        }
        
        # Headers
        headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': api_key
        }
        
        # Envoyer la requête POST à l'API
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        # Vérifier le succès
        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            if result.get('success'):
                url = result.get('url', '')
                logging.info(f"✅ Fichier '{filename}' publié via API sur {url}")
                return True
            else:
                logging.error(f"❌ Erreur API: {result.get('message', 'Erreur inconnue')}")
                return False
        else:
            logging.error(f"❌ Erreur API (HTTP {response.status_code}): {response.text}")
            return False
            
    except requests.Timeout:
        logging.error("❌ Timeout lors de l'appel à l'API de publication")
        return False
    except Exception as e:
        logging.error(f"❌ Erreur de publication via API: {e}")
        return False
