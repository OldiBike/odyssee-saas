# app.py - Application Flask SaaS Multi-Agences Odyssée
import os
from datetime import datetime, date
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, g, abort
from flask_migrate import Migrate
from flask_mail import Mail
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv

# Import des modèles et configuration
from models import db, Agency, User, Client, Trip, Invoice
from config import get_config
from utils.crypto import init_crypto, decrypt_config, decrypt_api_key

# Charger les variables d'environnement
load_dotenv()

# ==============================================================================
# INITIALISATION DE L'APPLICATION
# ==============================================================================

def create_app():
    """Factory pour créer l'application Flask."""
    
    app = Flask(__name__)
    
    # Charger la configuration
    app.config.from_object(get_config())
    
    # Initialiser les extensions
    db.init_app(app)
    Migrate(app, db)
    Mail(app)
    CORS(app)
    bcrypt = Bcrypt(app)
    
    # Initialiser le système de chiffrement
    init_crypto(app.config['MASTER_ENCRYPTION_KEY'])
    
    print("✅ Application Flask initialisée")
    
    # ==============================================================================
    # MIDDLEWARE - IDENTIFICATION DE L'AGENCE
    # ==============================================================================
    
    @app.before_request
    def identify_agency():
        """
        Identifie l'agence active selon le sous-domaine.
        Exemple: agence-x.odyssee.com → charge l'agence avec subdomain='agence-x'
        """
        # Extraire le host
        host = request.host.split(':')[0]  # Enlève le port si présent
        
        # Extraire le sous-domaine
        parts = host.split('.')
        
        # Cas spéciaux : localhost, admin, super-admin
        if host == 'localhost' or host == '127.0.0.1':
            subdomain = 'default'
        elif parts[0] in ['www', 'admin', 'super-admin']:
            subdomain = 'default'
        else:
            subdomain = parts[0] if len(parts) > 1 else 'default'
        
        # Charger l'agence depuis la base de données
        agency = Agency.query.filter_by(subdomain=subdomain, is_active=True).first()
        
        # Si aucune agence trouvée et qu'on n'est pas sur une route d'initialisation
        if not agency and not request.path.startswith('/init'):
            # En développement, on redirige vers l'initialisation
            if app.config['DEBUG']:
                return redirect('/init')
            else:
                abort(404, "Agence non trouvée")
        
        # Stocker l'agence dans le contexte global (accessible partout)
        g.agency = agency
        
        # Déchiffrer et stocker les configs de l'agence si elle existe
        if agency:
            g.agency_config = {
                'google_api_key': decrypt_api_key(agency.google_api_key_encrypted) if agency.google_api_key_encrypted else None,
                'stripe_api_key': decrypt_api_key(agency.stripe_api_key_encrypted) if agency.stripe_api_key_encrypted else None,
                'mail_config': decrypt_config(agency.mail_config_encrypted) if agency.mail_config_encrypted else {},
                'ftp_config': decrypt_config(agency.ftp_config_encrypted) if agency.ftp_config_encrypted else {},
            }
    
    # ==============================================================================
    # DÉCORATEURS D'AUTHENTIFICATION
    # ==============================================================================
    
    def login_required(f):
        """Vérifie que l'utilisateur est connecté."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            
            # Charger l'utilisateur
            g.user = User.query.get(session['user_id'])
            if not g.user or not g.user.is_active:
                session.clear()
                return redirect(url_for('login'))
            
            return f(*args, **kwargs)
        return decorated_function
    
    def super_admin_required(f):
        """Vérifie que l'utilisateur est super-admin."""
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if g.user.role != 'super_admin':
                abort(403, "Accès réservé aux super-administrateurs")
            return f(*args, **kwargs)
        return decorated_function
    
    def agency_admin_required(f):
        """Vérifie que l'utilisateur est admin de son agence."""
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if g.user.role not in ['super_admin', 'agency_admin']:
                abort(403, "Accès réservé aux administrateurs")
            return f(*args, **kwargs)
        return decorated_function
    
    # ==============================================================================
    # COMMANDE CLI - INITIALISATION
    # ==============================================================================
    
    @app.cli.command("init-db")
    def init_db_command():
        """Initialise la base de données et crée le super-admin."""
        with app.app_context():
            # Créer toutes les tables
            db.create_all()
            print("✅ Base de données créée")
            
            # Vérifier si le super-admin existe déjà
            super_admin = User.query.filter_by(role='super_admin').first()
            if not super_admin:
                # Créer le super-admin
                hashed_password = bcrypt.generate_password_hash(
                    app.config['SUPER_ADMIN_PASSWORD']
                ).decode('utf-8')
                
                super_admin = User(
                    username=app.config['SUPER_ADMIN_USERNAME'],
                    password=hashed_password,
                    pseudo='Super Admin',
                    email=app.config['SUPER_ADMIN_EMAIL'],
                    role='super_admin',
                    agency_id=None  # Super admin n'appartient à aucune agence
                )
                db.session.add(super_admin)
                db.session.commit()
                
                print(f"✅ Super-admin créé : {super_admin.username}")
                print(f"   Email: {super_admin.email}")
                print(f"   Mot de passe: {app.config['SUPER_ADMIN_PASSWORD']}")
            else:
                print(f"ℹ️  Super-admin existe déjà : {super_admin.username}")
    
    # ==============================================================================
    # ROUTES D'AUTHENTIFICATION
    # ==============================================================================
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Page de connexion."""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = User.query.filter_by(username=username, is_active=True).first()
            
            if user and bcrypt.check_password_hash(user.password, password):
                # Vérifier que l'utilisateur appartient à l'agence (sauf super_admin)
                if user.role != 'super_admin' and user.agency_id != g.agency.id:
                    return render_template('login.html', error="Accès non autorisé à cette agence")
                
                # Connexion réussie
                session.clear()
                session['user_id'] = user.id
                session['role'] = user.role
                session['agency_id'] = user.agency_id
                
                # Redirection selon le rôle
                if user.role == 'super_admin':
                    return redirect(url_for('super_admin_dashboard'))
                else:
                    return redirect(url_for('home'))
            else:
                return render_template('login.html', error="Identifiants incorrects")
        
        return render_template('login.html')
    
    @app.route('/logout')
    def logout():
        """Déconnexion."""
        session.clear()
        return redirect(url_for('login'))
    
    # ==============================================================================
    # ROUTES PRINCIPALES
    # ==============================================================================
    
    @app.route('/')
    @login_required
    def home():
        """Page d'accueil (redirige selon le rôle)."""
        if g.user.role == 'super_admin':
            return redirect(url_for('super_admin_dashboard'))
        else:
            return render_template('home.html', agency=g.agency)
    
    # ==============================================================================
    # ROUTES SUPER-ADMIN
    # ==============================================================================
    
    @app.route('/super-admin')
    @super_admin_required
    def super_admin_dashboard():
        """Dashboard du super-administrateur."""
        # Statistiques globales
        total_agencies = Agency.query.count()
        active_agencies = Agency.query.filter_by(is_active=True).count()
        total_users = User.query.filter(User.role != 'super_admin').count()
        total_trips = Trip.query.count()
        
        stats = {
            'total_agencies': total_agencies,
            'active_agencies': active_agencies,
            'total_users': total_users,
            'total_trips': total_trips
        }
        
        return render_template('super_admin/dashboard.html', stats=stats)
    
    @app.route('/super-admin/agencies')
    @super_admin_required
    def agencies_list():
        """Liste des agences."""
        return render_template('super_admin/agencies.html')
    
    @app.route('/api/super-admin/agencies', methods=['GET', 'POST'])
    @super_admin_required
    def api_agencies():
        """API CRUD pour les agences."""
        if request.method == 'GET':
            agencies = Agency.query.all()
            return jsonify([agency.to_dict() for agency in agencies])
        
        elif request.method == 'POST':
            # Créer une nouvelle agence
            data = request.get_json()
            
            # Vérifier que le sous-domaine n'existe pas déjà
            existing = Agency.query.filter_by(subdomain=data['subdomain']).first()
            if existing:
                return jsonify({'success': False, 'message': 'Ce sous-domaine existe déjà'}), 400
            
            try:
                from utils.crypto import encrypt_api_key, encrypt_config
                
                new_agency = Agency(
                    name=data['name'],
                    subdomain=data['subdomain'],
                    logo_url=data.get('logo_url'),
                    primary_color=data.get('primary_color', '#3B82F6'),
                    template_name=data.get('template_name', 'classic'),
                    contact_email=data.get('contact_email'),
                    contact_phone=data.get('contact_phone'),
                    subscription_tier=data.get('subscription_tier', 'basic'),
                    monthly_generation_limit=int(data.get('monthly_generation_limit', 100))
                )
                
                # Chiffrer les configs si fournies
                if data.get('google_api_key'):
                    new_agency.google_api_key_encrypted = encrypt_api_key(data['google_api_key'])
                
                if data.get('stripe_api_key'):
                    new_agency.stripe_api_key_encrypted = encrypt_api_key(data['stripe_api_key'])
                
                if data.get('mail_config'):
                    new_agency.mail_config_encrypted = encrypt_config(data['mail_config'])
                
                db.session.add(new_agency)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Agence créée avec succès',
                    'agency': new_agency.to_dict()
                })
                
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': str(e)}), 500
    
    # ==============================================================================
    # ROUTE D'INITIALISATION (première installation)
    # ==============================================================================
    
    @app.route('/init')
    def init_setup():
        """Page d'initialisation pour la première installation."""
        # Vérifier si la DB est déjà initialisée
        try:
            if Agency.query.first() is not None:
                return redirect(url_for('login'))
        except:
            pass
        
        return """
        <html>
        <head><title>Initialisation Odyssée</title></head>
        <body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h1>🚀 Bienvenue sur Odyssée SaaS !</h1>
            <p>L'application n'est pas encore initialisée.</p>
            <h2>📋 Étapes d'initialisation :</h2>
            <ol>
                <li><strong>Ouvrez un terminal</strong></li>
                <li><strong>Lancez :</strong> <code>flask init-db</code></li>
                <li><strong>Redémarrez l'application</strong></li>
                <li><strong>Connectez-vous</strong> avec les identifiants du super-admin (dans votre .env)</li>
            </ol>
            <p>Une fois connecté en tant que super-admin, vous pourrez créer votre première agence !</p>
        </body>
        </html>
        """
    
    # ==============================================================================
    # GESTION DES ERREURS
    # ==============================================================================
    
    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'error': 'Accès refusé', 'message': str(e)}), 403
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Non trouvé', 'message': str(e)}), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return jsonify({'error': 'Erreur serveur', 'message': str(e)}), 500
    
    return app


# ==============================================================================
# POINT D'ENTRÉE
# ==============================================================================

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)