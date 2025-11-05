#!/bin/bash
# Script pour lancer Flask en local avec SQLite (développement)

echo "🚀 Démarrage de Flask en mode développement local..."
echo "📍 URL: http://localhost:5001"
echo "🗄️  Base de données: SQLite local (instance/odyssee.db)"
echo ""
echo "ℹ️  Pour utiliser PostgreSQL Railway, utilisez: railway run flask run --port=5001"
echo ""

# Enlève DATABASE_URL pour forcer l'utilisation de SQLite en local
unset DATABASE_URL

export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1

flask run --port=5001
