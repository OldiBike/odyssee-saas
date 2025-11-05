#!/bin/bash
# Script de démarrage pour Railway

echo "🔧 Initialisation de la base de données..."

# Créer le répertoire instance si nécessaire
mkdir -p instance

# Exécuter les migrations Flask
echo "📊 Application des migrations..."
flask db upgrade

# Toujours exécuter init-db pour initialiser si nécessaire (il skip si déjà initialisé)
echo "🔧 Initialisation de la base de données (si nécessaire)..."
flask init-db

echo "✅ Base de données prête"

# Démarrer l'application avec gunicorn
echo "🚀 Démarrage de l'application..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 2 --worker-class gthread --timeout 120 --access-logfile - --error-logfile - app:app
