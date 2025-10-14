from app import app, db
from models import Agency

with app.app_context():
    # Vérifier si une agence existe déjà
    existing = Agency.query.first()
    if existing:
        print(f"ℹ️  Une agence existe déjà : {existing.name}")
    else:
        # Créer l'agence par défaut
        default_agency = Agency(
            name="Voyages Privilèges",
            subdomain="default",
            primary_color="#3B82F6",
            template_name="classic",
            contact_email="info@voyages-privileges.be",
            contact_phone="+32 488 43 33 44",
            is_active=True,
            monthly_generation_limit=100
        )
        db.session.add(default_agency)
        db.session.commit()
        print("✅ Agence 'Voyages Privilèges' créée avec succès !")
        print(f"   ID: {default_agency.id}")
        print(f"   Sous-domaine: {default_agency.subdomain}")