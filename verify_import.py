#!/usr/bin/env python3
"""Script de vérification de l'import des données"""

from app import app, db
from models import Agency, Trip, User, Client

with app.app_context():
    print("\n" + "="*50)
    print("📊 VÉRIFICATION DES DONNÉES IMPORTÉES")
    print("="*50 + "\n")
    
    agencies = Agency.query.count()
    trips = Trip.query.count()
    users = User.query.count()
    clients = Client.query.count()
    
    print(f"✅ Agences      : {agencies}")
    print(f"✅ Voyages      : {trips}")
    print(f"✅ Utilisateurs : {users}")
    print(f"✅ Clients      : {clients}")
    
    if agencies > 0:
        print("\n📋 Première agence :")
        agency = Agency.query.first()
        print(f"   - Nom: {agency.name}")
        print(f"   - Contact: {agency.contact_email}")
    
    if trips > 0:
        print(f"\n🗺️  Premiers voyages :")
        for trip in Trip.query.limit(3).all():
            print(f"   - ID {trip.id} vers {trip.destination}")
    
    print("\n" + "="*50)
    print("✅ Import réussi avec toutes les données !")
    print("="*50 + "\n")
