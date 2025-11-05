#!/usr/bin/env python3
"""
Script pour importer des données depuis une URL
Utile pour Railway quand le fichier SQL est trop gros pour être uploadé directement
"""

import os
import sys
import requests
from urllib.parse import urlparse

def download_and_import(url):
    """
    Télécharge un fichier SQL depuis une URL et l'importe
    """
    print(f"📥 Téléchargement du fichier SQL depuis : {url}")
    
    try:
        # Télécharger le fichier
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        # Nom du fichier temporaire
        temp_file = 'import_temp.sql'
        
        # Sauvegarder le fichier
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r📊 Téléchargé : {percent:.1f}%", end='', flush=True)
        
        print(f"\n✅ Fichier téléchargé : {downloaded / 1024 / 1024:.2f} Mo")
        
        # Importer le fichier
        print("📊 Lancement de l'import...")
        exit_code = os.system(f'flask import-data {temp_file}')
        
        # Nettoyer
        if os.path.exists(temp_file):
            os.remove(temp_file)
            print("🧹 Fichier temporaire supprimé")
        
        if exit_code == 0:
            print("✅ Import terminé avec succès !")
            return True
        else:
            print(f"❌ L'import a échoué avec le code : {exit_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors du téléchargement : {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return False

def main():
    """
    Point d'entrée principal
    """
    # Vérifier la variable d'environnement
    sql_url = os.getenv('SQL_IMPORT_URL')
    
    if not sql_url:
        print("❌ Variable d'environnement SQL_IMPORT_URL non définie")
        print("\n📋 Pour utiliser ce script :")
        print("1. Hébergez votre fichier SQL sur Dropbox, Google Drive, etc.")
        print("2. Obtenez le lien de téléchargement direct")
        print("3. Définissez la variable : export SQL_IMPORT_URL='votre-lien'")
        print("4. Relancez ce script : python import_from_url.py")
        print("\nOu passez l'URL en argument : python import_from_url.py https://...")
        sys.exit(1)
    
    # Ou depuis les arguments
    if len(sys.argv) > 1:
        sql_url = sys.argv[1]
    
    print(f"🎯 URL du fichier SQL : {sql_url}")
    
    # Valider l'URL
    try:
        result = urlparse(sql_url)
        if not all([result.scheme, result.netloc]):
            print("❌ URL invalide")
            sys.exit(1)
    except Exception:
        print("❌ URL invalide")
        sys.exit(1)
    
    # Télécharger et importer
    success = download_and_import(sql_url)
    
    if success:
        print("\n🎉 Données importées avec succès !")
        print("Vous pouvez maintenant vous connecter à votre application.")
        sys.exit(0)
    else:
        print("\n❌ L'import a échoué")
        sys.exit(1)

if __name__ == '__main__':
    main()
