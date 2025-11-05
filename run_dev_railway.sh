#!/bin/bash
# Script pour lancer Flask en local connecté à PostgreSQL Railway

echo "🚀 Démarrage de Flask en local avec PostgreSQL Railway..."
echo "📍 URL: http://localhost:5001"
echo "🗄️  Base de données: PostgreSQL Railway (production)"
echo "⚠️  ATTENTION: Vous travaillez sur la base de données de PRODUCTION!"
echo ""

# Utilise Railway pour injecter les variables d'environnement
railway run flask run --port=5001
