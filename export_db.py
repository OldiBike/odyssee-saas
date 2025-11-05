#!/usr/bin/env python3
"""
Script pour exporter la base de données SQLite en SQL
Usage: python export_db.py
"""

import sqlite3
import os
from datetime import datetime

# Chemin de la base de données
DB_PATH = 'instance/odyssee.db'
OUTPUT_FILE = f'db_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'

def export_database():
    """Exporte toute la base de données en SQL"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Base de données non trouvée : {DB_PATH}")
        return False
    
    print(f"📊 Export de la base de données : {DB_PATH}")
    print(f"📝 Fichier de sortie : {OUTPUT_FILE}")
    
    try:
        # Connexion à la base de données
        conn = sqlite3.connect(DB_PATH)
        
        # Ouvrir le fichier de sortie
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            # Header
            f.write("-- Export automatique de la base Odyssée\n")
            f.write(f"-- Date: {datetime.now()}\n")
            f.write("-- ATTENTION: Exécuter ce fichier va écraser les données existantes\n\n")
            
            # Désactiver les contraintes FK temporairement
            f.write("PRAGMA foreign_keys=OFF;\n")
            f.write("BEGIN TRANSACTION;\n\n")
            
            # Itérer sur toutes les lignes exportées
            for line in conn.iterdump():
                # Ignorer les lignes de transaction (on les gère nous-mêmes)
                if line not in ['BEGIN TRANSACTION;', 'COMMIT;']:
                    # Écrire la ligne
                    f.write(f'{line}\n')
            
            # Réactiver les contraintes et committer
            f.write("\nCOMMIT;\n")
            f.write("PRAGMA foreign_keys=ON;\n")
        
        conn.close()
        
        # Statistiques
        file_size = os.path.getsize(OUTPUT_FILE) / 1024  # Ko
        
        print(f"✅ Export réussi !")
        print(f"📦 Taille : {file_size:.2f} Ko")
        print(f"\n📋 Prochaine étape :")
        print(f"   1. Copiez le fichier {OUTPUT_FILE}")
        print(f"   2. Sur Railway, exécutez : flask import-data {OUTPUT_FILE}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'export : {e}")
        return False

if __name__ == '__main__':
    export_database()
