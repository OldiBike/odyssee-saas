#!/bin/bash
# Script pour lancer Flask en local avec SQLite (isolation)

echo "🚀 Démarrage de Flask en mode développement local..."
echo "📍 URL: http://localhost:5001"
echo "🗄️  Base de données: SQLite local (instance/odyssee.db)"
echo ""
echo "💡 Pour utiliser PostgreSQL Railway, lancez: ./run_dev.sh"
echo ""

# Enlève DATABASE_URL pour forcer SQLite
unset DATABASE_URL

export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1

flask run --port=5001
