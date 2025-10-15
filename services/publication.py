# services/publication.py
"""
Service de publication des fiches de voyage sur des serveurs externes.
Pour l'instant, supporte uniquement FTP.
"""

import ftplib
import tempfile
import os
from typing import Dict


def publish_via_ftp(html_content: str, filename: str, ftp_config: Dict[str, str]) -> bool:
    """
    Publie un contenu HTML sur un serveur FTP.

    Args:
        html_content (str): Le contenu HTML à publier.
        filename (str): Le nom du fichier à créer sur le serveur distant.
        ftp_config (dict): Dictionnaire contenant 'host', 'user', 'password', 'path'.

    Returns:
        bool: True si la publication a réussi, False sinon.
    """
    host = ftp_config.get('host')
    user = ftp_config.get('user')
    password = ftp_config.get('password')
    remote_path = ftp_config.get('path', '/')

    if not all([host, user, password]):
        raise ValueError("Configuration FTP incomplète (host, user, password sont requis).")

    # Créer un fichier temporaire avec le contenu HTML
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.html', encoding='utf-8') as tmp_file:
        tmp_file.write(html_content)
        local_filepath = tmp_file.name

    try:
        # Connexion au serveur FTP
        with ftplib.FTP(host, user, password, timeout=10) as ftp:
            # Se déplacer vers le bon répertoire
            if remote_path and remote_path != '/':
                try:
                    ftp.cwd(remote_path)
                except ftplib.error_perm:
                    # Essayer de créer le répertoire s'il n'existe pas
                    ftp.mkd(remote_path)
                    ftp.cwd(remote_path)

            # Uploader le fichier
            with open(local_filepath, 'rb') as file_to_upload:
                ftp.storbinary(f'STOR {filename}', file_to_upload)
        
        print(f"✅ Fichier '{filename}' publié avec succès sur {host}:{remote_path}")
        return True

    except Exception as e:
        print(f"❌ Erreur de publication FTP: {e}")
        return False
    finally:
        # Supprimer le fichier temporaire
        if os.path.exists(local_filepath):
            os.remove(local_filepath)