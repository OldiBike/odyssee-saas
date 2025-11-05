#!/bin/bash
# Script pour lancer Flask sur le port 5001 (évite conflit avec AirPlay sur 5000)

export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1

echo "🚀 Démarrage de Flask sur le port 5001..."
echo "📍 URL: http://localhost:5001"
echo ""

flask run --port=5001
