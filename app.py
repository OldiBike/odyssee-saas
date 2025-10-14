# app.py - Application Flask SaaS Multi-Agences Odyssée
import os
import json
import requests
from datetime import datetime, date, timedelta
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
    
    def agency_required(f):
        """Vérifie que l'utilisateur appartient à une agence (admin ou seller)."""
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if g.user.role == 'super_admin':
                # Super admin n'a pas accès aux interfaces agence
                abort(403, "Cette page est réservée aux agences")
            
            if g.user.role not in ['agency_admin', 'seller']:
                abort(403, "Accès réservé aux membres d'agence")
            
            # Vérifier que l'agence est active
            if not g.agency or not g.agency.is_active:
                abort(403, "Votre agence est désactivée")
            
            return f(*args, **kwargs)
        return decorated_function
    
    # ==============================================================================
    # FONCTIONS HELPER POUR LES QUOTAS
    # ==============================================================================
    
    def check_generation_quota(user, agency):
        """
        Vérifie si l'utilisateur peut générer un voyage
        
        Returns:
            bool: True si quota OK, False sinon
        """
        # Vérifier quota quotidien du vendeur
        today = date.today()
        if user.last_generation_date != today:
            # Réinitialiser le compteur si on change de jour
            user.generation_count = 0
            user.last_generation_date = today
            db.session.commit()
        
        if user.generation_count >= user.daily_generation_limit:
            return False
        
        # Vérifier quota mensuel de l'agence
        if agency.usage_reset_date < today:
            # Réinitialiser le compteur mensuel
            agency.current_month_usage = 0
            # Calculer la prochaine date de reset (1er du mois prochain)
            if today.month == 12:
                agency.usage_reset_date = date(today.year + 1, 1, 1)
            else:
                agency.usage_reset_date = date(today.year, today.month + 1, 1)
            db.session.commit()
        
        if agency.current_month_usage >= agency.monthly_generation_limit:
            return False
        
        return True
    
    def increment_generation_counters(user, agency):
        """Incrémente les compteurs de génération"""
        user.generation_count += 1
        agency.current_month_usage += 1
        db.session.commit()
    
    def calculate_duration_minutes(data):
        """
        Calcule la durée de trajet en minutes depuis les données du formulaire
        
        Args:
            data: Données du formulaire contenant travel_hours et travel_minutes
            
        Returns:
            int: Durée totale en minutes
        """
        form_data = data.get('form_data', {})
        hours = int(form_data.get('travel_hours', 0))
        minutes = int(form_data.get('travel_minutes', 0))
        return (hours * 60) + minutes
    
    # ==============================================================================
    # HELPER POUR RÉCUPÉRER LA CLÉ GOOGLE API
    # ==============================================================================
    
    def get_google_api_key():
        """
        Récupère la clé Google API (agence en priorité, sinon globale)
        
        Returns:
            str: Clé API Google ou None
        """
        # Priorité 1 : Clé de l'agence (chiffrée en BDD)
        if hasattr(g, 'agency_config') and g.agency_config.get('google_api_key'):
            return g.agency_config['google_api_key']
        
        # Priorité 2 : Clé globale depuis .env
        return app.config.get('GOOGLE_PLACES_API_KEY')
    
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
                    return redirect(url_for('agency_dashboard'))
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
            return redirect(url_for('agency_dashboard'))
    
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
    
    @app.route('/super-admin/agencies/<int:agency_id>/users')
    @super_admin_required
    def agency_users(agency_id):
        """Page de gestion des utilisateurs d'une agence."""
        agency = Agency.query.get_or_404(agency_id)
        return render_template('super_admin/agency_users.html', agency=agency)
    
    # ==============================================================================
    # API SUPER-ADMIN - GESTION DES AGENCES
    # ==============================================================================
    
    @app.route('/api/super-admin/agencies', methods=['GET', 'POST'])
    @super_admin_required
    def api_agencies():
        """API CRUD pour les agences - GET et POST."""
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
    
    @app.route('/api/super-admin/agencies/<int:agency_id>', methods=['GET', 'PUT', 'DELETE'])
    @super_admin_required
    def api_agency_detail(agency_id):
        """API CRUD pour une agence spécifique - GET, PUT, DELETE."""
        agency = Agency.query.get_or_404(agency_id)
        
        if request.method == 'GET':
            # Retourner les détails de l'agence
            return jsonify(agency.to_dict())
        
        elif request.method == 'PUT':
            # Modifier l'agence
            data = request.get_json()
            
            try:
                from utils.crypto import encrypt_api_key, encrypt_config
                
                # Mise à jour des champs de base
                agency.name = data.get('name', agency.name)
                
                # Vérifier le sous-domaine seulement s'il a changé
                new_subdomain = data.get('subdomain')
                if new_subdomain and new_subdomain != agency.subdomain:
                    existing = Agency.query.filter_by(subdomain=new_subdomain).first()
                    if existing:
                        return jsonify({'success': False, 'message': 'Ce sous-domaine existe déjà'}), 400
                    agency.subdomain = new_subdomain
                
                agency.logo_url = data.get('logo_url', agency.logo_url)
                agency.primary_color = data.get('primary_color', agency.primary_color)
                agency.template_name = data.get('template_name', agency.template_name)
                agency.contact_email = data.get('contact_email', agency.contact_email)
                agency.contact_phone = data.get('contact_phone', agency.contact_phone)
                agency.subscription_tier = data.get('subscription_tier', agency.subscription_tier)
                agency.monthly_generation_limit = int(data.get('monthly_generation_limit', agency.monthly_generation_limit))
                agency.is_active = data.get('is_active', agency.is_active)
                
                # Mise à jour des clés API si fournies (seulement si non vides)
                if data.get('google_api_key'):
                    agency.google_api_key_encrypted = encrypt_api_key(data['google_api_key'])
                
                if data.get('stripe_api_key'):
                    agency.stripe_api_key_encrypted = encrypt_api_key(data['stripe_api_key'])
                
                if data.get('mail_config'):
                    agency.mail_config_encrypted = encrypt_config(data['mail_config'])
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Agence modifiée avec succès',
                    'agency': agency.to_dict()
                })
                
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': str(e)}), 500
        
        elif request.method == 'DELETE':
            # Supprimer l'agence
            try:
                # Vérifier s'il y a des utilisateurs ou des voyages associés
                users_count = User.query.filter_by(agency_id=agency_id).count()
                trips_count = Trip.query.filter_by(agency_id=agency_id).count()
                
                if users_count > 0 or trips_count > 0:
                    return jsonify({
                        'success': False,
                        'message': f'Impossible de supprimer : {users_count} utilisateur(s) et {trips_count} voyage(s) associé(s). Désactivez plutôt l\'agence.'
                    }), 400
                
                # Supprimer l'agence
                db.session.delete(agency)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Agence supprimée avec succès'
                })
                
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': str(e)}), 500
    
    # ==============================================================================
    # API SUPER-ADMIN - GESTION DES UTILISATEURS
    # ==============================================================================
    
    @app.route('/api/super-admin/agencies/<int:agency_id>/users', methods=['GET', 'POST'])
    @super_admin_required
    def api_agency_users(agency_id):
        """API pour les utilisateurs d'une agence - GET et POST."""
        agency = Agency.query.get_or_404(agency_id)
        
        if request.method == 'GET':
            # Liste des utilisateurs de l'agence
            users = User.query.filter_by(agency_id=agency_id).all()
            return jsonify([user.to_dict() for user in users])
        
        elif request.method == 'POST':
            # Créer un nouvel utilisateur
            data = request.get_json()
            
            # Vérifier que le username n'existe pas déjà
            existing = User.query.filter_by(username=data['username']).first()
            if existing:
                return jsonify({'success': False, 'message': 'Ce nom d\'utilisateur existe déjà'}), 400
            
            # Vérifier que l'email n'existe pas déjà
            existing_email = User.query.filter_by(email=data['email']).first()
            if existing_email:
                return jsonify({'success': False, 'message': 'Cet email existe déjà'}), 400
            
            try:
                # Hash du mot de passe
                hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
                
                new_user = User(
                    agency_id=agency_id,
                    username=data['username'],
                    password=hashed_password,
                    pseudo=data['pseudo'],
                    email=data['email'],
                    phone=data.get('phone'),
                    role=data.get('role', 'seller'),
                    margin_percentage=int(data.get('margin_percentage', 80)),
                    daily_generation_limit=int(data.get('daily_generation_limit', 5)),
                    is_active=True
                )
                
                db.session.add(new_user)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Utilisateur créé avec succès',
                    'user': new_user.to_dict()
                })
                
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/super-admin/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
    @super_admin_required
    def api_user_detail(user_id):
        """API CRUD pour un utilisateur spécifique - GET, PUT, DELETE."""
        user = User.query.get_or_404(user_id)
        
        # Empêcher la modification du super-admin
        if user.role == 'super_admin':
            return jsonify({'success': False, 'message': 'Impossible de modifier le super-admin'}), 403
        
        if request.method == 'GET':
            return jsonify(user.to_dict())
        
        elif request.method == 'PUT':
            # Modifier l'utilisateur
            data = request.get_json()
            
            try:
                # Vérifier le username seulement s'il a changé
                new_username = data.get('username')
                if new_username and new_username != user.username:
                    existing = User.query.filter_by(username=new_username).first()
                    if existing:
                        return jsonify({'success': False, 'message': 'Ce nom d\'utilisateur existe déjà'}), 400
                    user.username = new_username
                
                # Vérifier l'email seulement s'il a changé
                new_email = data.get('email')
                if new_email and new_email != user.email:
                    existing = User.query.filter_by(email=new_email).first()
                    if existing:
                        return jsonify({'success': False, 'message': 'Cet email existe déjà'}), 400
                    user.email = new_email
                
                # Mise à jour des champs
                user.pseudo = data.get('pseudo', user.pseudo)
                user.phone = data.get('phone', user.phone)
                user.role = data.get('role', user.role)
                user.margin_percentage = int(data.get('margin_percentage', user.margin_percentage))
                user.daily_generation_limit = int(data.get('daily_generation_limit', user.daily_generation_limit))
                user.is_active = data.get('is_active', user.is_active)
                
                # Changer le mot de passe seulement s'il est fourni
                new_password = data.get('password')
                if new_password and new_password.strip():
                    user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Utilisateur modifié avec succès',
                    'user': user.to_dict()
                })
                
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': str(e)}), 500
        
        elif request.method == 'DELETE':
            # Supprimer/Désactiver l'utilisateur
            try:
                # Vérifier s'il y a des voyages associés
                trips_count = Trip.query.filter_by(user_id=user_id).count()
                
                if trips_count > 0:
                    # Désactiver au lieu de supprimer
                    user.is_active = False
                    db.session.commit()
                    return jsonify({
                        'success': True,
                        'message': f'Utilisateur désactivé ({trips_count} voyage(s) associé(s))'
                    })
                else:
                    # Supprimer définitivement
                    db.session.delete(user)
                    db.session.commit()
                    return jsonify({
                        'success': True,
                        'message': 'Utilisateur supprimé avec succès'
                    })
                
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': str(e)}), 500
    
    # ==============================================================================
    # ROUTES AGENCE - PAGES
    # ==============================================================================
    
    @app.route('/agency/dashboard')
    @agency_required
    def agency_dashboard():
        """Dashboard de l'agence (admin ou seller)"""
        
        # Statistiques selon le rôle
        if g.user.role == 'agency_admin':
            # Admin voit toute l'agence
            total_trips = Trip.query.filter_by(agency_id=g.agency.id).count()
            proposed_trips = Trip.query.filter_by(
                agency_id=g.agency.id, 
                status='proposed'
            ).count()
            assigned_trips = Trip.query.filter_by(
                agency_id=g.agency.id, 
                status='assigned'
            ).count()
            sold_trips = Trip.query.filter_by(
                agency_id=g.agency.id, 
                status='sold'
            ).count()
            total_clients = Client.query.filter_by(agency_id=g.agency.id).count()
            
        else:
            # Seller voit seulement ses voyages
            total_trips = Trip.query.filter_by(
                agency_id=g.agency.id,
                user_id=g.user.id
            ).count()
            proposed_trips = Trip.query.filter_by(
                agency_id=g.agency.id,
                user_id=g.user.id,
                status='proposed'
            ).count()
            assigned_trips = Trip.query.filter_by(
                agency_id=g.agency.id,
                user_id=g.user.id,
                status='assigned'
            ).count()
            sold_trips = Trip.query.filter_by(
                agency_id=g.agency.id,
                user_id=g.user.id,
                status='sold'
            ).count()
            total_clients = 0  # Le seller n'a pas accès à tous les clients
        
        stats = {
            'total_trips': total_trips,
            'proposed_trips': proposed_trips,
            'assigned_trips': assigned_trips,
            'sold_trips': sold_trips,
            'total_clients': total_clients,
            'quota_used': g.user.generation_count,
            'quota_limit': g.user.daily_generation_limit,
            'agency_quota_used': g.agency.current_month_usage,
            'agency_quota_limit': g.agency.monthly_generation_limit
        }
        
        return render_template('agency/dashboard.html', stats=stats)
    
    @app.route('/agency/generate')
    @agency_required
    def generate_trip():
        """Page de génération de voyage avec Wizard IA"""
        
        # Vérifier que l'agence a une clé Google API (agence ou globale)
        google_api_key = get_google_api_key()
        
        if not google_api_key:
            return render_template('error.html', 
                                 message='Aucune clé Google API configurée. Contactez votre administrateur.')
        
        # Vérifier le quota
        if not check_generation_quota(g.user, g.agency):
            return render_template('error.html',
                                 message='Quota de génération atteint. Réessayez demain ou contactez votre administrateur.')
        
        # ⚠️ SÉCURITÉ : On ne passe PLUS la clé au template
        # Les appels Google se feront via les routes proxy
        return render_template('agency/generate.html',
                             user_margin=g.user.margin_percentage)
    
    @app.route('/agency/trips')
    @agency_required
    def trips_list():
        """Liste des voyages de l'agence"""
        
        # Selon le rôle, filtrer les voyages
        if g.user.role == 'agency_admin':
            trips = Trip.query.filter_by(agency_id=g.agency.id).order_by(
                Trip.created_at.desc()
            ).all()
        else:
            # Seller voit seulement ses voyages
            trips = Trip.query.filter_by(
                agency_id=g.agency.id,
                user_id=g.user.id
            ).order_by(Trip.created_at.desc()).all()
        
        return render_template('agency/trips.html', trips=trips)
    
    @app.route('/agency/clients')
    @agency_required
    def clients_list():
        """Gestion des clients de l'agence"""
        
        # Seuls les admins ont accès à la liste complète des clients
        if g.user.role != 'agency_admin':
            abort(403, "Accès réservé aux administrateurs d'agence")
        
        clients = Client.query.filter_by(agency_id=g.agency.id).order_by(
            Client.created_at.desc()
        ).all()
        
        return render_template('agency/clients.html', clients=clients)
    
    # ==============================================================================
    # 🔒 ROUTES PROXY GOOGLE API (SÉCURISÉES)
    # ==============================================================================
    
    @app.route('/api/google/autocomplete', methods=['POST'])
    @agency_required
    def proxy_google_autocomplete():
        """
        🔒 Proxy sécurisé pour Google Places Autocomplete
        La clé API reste côté serveur, jamais exposée au client
        """
        try:
            data = request.get_json()
            input_text = data.get('input', '')
            
            if not input_text or len(input_text) < 3:
                return jsonify({
                    'success': False,
                    'error': 'Veuillez saisir au moins 3 caractères'
                }), 400
            
            # Récupérer la clé API (agence ou globale)
            api_key = get_google_api_key()
            
            if not api_key:
                return jsonify({
                    'success': False,
                    'error': 'Clé Google API non configurée'
                }), 500
            
            # Appeler l'API Google Places Autocomplete
            url = 'https://maps.googleapis.com/maps/api/place/autocomplete/json'
            params = {
                'input': input_text,
                'types': 'establishment|lodging',  # Hôtels et établissements
                'key': api_key,
                'language': 'fr'
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                return jsonify({
                    'success': True,
                    'predictions': result.get('predictions', [])
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Erreur API Google'
                }), response.status_code
                
        except requests.Timeout:
            return jsonify({
                'success': False,
                'error': 'Timeout - API Google ne répond pas'
            }), 504
        except Exception as e:
            print(f"❌ Erreur proxy autocomplete: {e}")
            return jsonify({
                'success': False,
                'error': f'Erreur serveur: {str(e)}'
            }), 500
    
    @app.route('/api/google/place-details', methods=['POST'])
    @agency_required
    def proxy_google_place_details():
        """
        🔒 Proxy sécurisé pour Google Places Details
        Récupère les détails d'un lieu (adresse, photos, etc.)
        """
        try:
            data = request.get_json()
            place_id = data.get('place_id')
            
            if not place_id:
                return jsonify({
                    'success': False,
                    'error': 'Place ID requis'
                }), 400
            
            # Récupérer la clé API
            api_key = get_google_api_key()
            
            if not api_key:
                return jsonify({
                    'success': False,
                    'error': 'Clé Google API non configurée'
                }), 500
            
            # Appeler l'API Google Places Details
            url = 'https://maps.googleapis.com/maps/api/place/details/json'
            params = {
                'place_id': place_id,
                'fields': 'name,formatted_address,geometry,photos,rating,user_ratings_total,types',
                'key': api_key,
                'language': 'fr'
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                return jsonify({
                    'success': True,
                    'result': result.get('result', {})
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Erreur API Google'
                }), response.status_code
                
        except requests.Timeout:
            return jsonify({
                'success': False,
                'error': 'Timeout - API Google ne répond pas'
            }), 504
        except Exception as e:
            print(f"❌ Erreur proxy place details: {e}")
            return jsonify({
                'success': False,
                'error': f'Erreur serveur: {str(e)}'
            }), 500
    
    @app.route('/api/google/place-photos', methods=['POST'])
    @agency_required
    def proxy_google_place_photos():
        """
        🔒 Proxy sécurisé pour Google Places Photos
        Récupère les URLs des photos d'un lieu
        """
        try:
            data = request.get_json()
            photo_reference = data.get('photo_reference')
            max_width = data.get('max_width', 800)
            
            if not photo_reference:
                return jsonify({
                    'success': False,
                    'error': 'Photo reference requise'
                }), 400
            
            # Récupérer la clé API
            api_key = get_google_api_key()
            
            if not api_key:
                return jsonify({
                    'success': False,
                    'error': 'Clé Google API non configurée'
                }), 500
            
            # Construire l'URL de la photo
            photo_url = f'https://maps.googleapis.com/maps/api/place/photo'
            params = {
                'photoreference': photo_reference,
                'maxwidth': max_width,
                'key': api_key
            }
            
            # Retourner l'URL (la requête finale sera faite par le navigateur)
            # Mais sans exposer la clé
            return jsonify({
                'success': True,
                'photo_url': f"{photo_url}?photoreference={photo_reference}&maxwidth={max_width}&key={api_key}"
            })
                
        except Exception as e:
            print(f"❌ Erreur proxy photos: {e}")
            return jsonify({
                'success': False,
                'error': f'Erreur serveur: {str(e)}'
            }), 500
    
    @app.route('/api/google/nearby-search', methods=['POST'])
    @agency_required
    def proxy_google_nearby_search():
        """
        🔒 Proxy sécurisé pour Google Places Nearby Search
        Recherche des lieux à proximité d'un point
        """
        try:
            data = request.get_json()
            location = data.get('location')  # Format: "lat,lng"
            radius = data.get('radius', 5000)  # Rayon en mètres
            place_type = data.get('type', 'tourist_attraction')
            
            if not location:
                return jsonify({
                    'success': False,
                    'error': 'Location requise (lat,lng)'
                }), 400
            
            # Récupérer la clé API
            api_key = get_google_api_key()
            
            if not api_key:
                return jsonify({
                    'success': False,
                    'error': 'Clé Google API non configurée'
                }), 500
            
            # Appeler l'API Google Places Nearby Search
            url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
            params = {
                'location': location,
                'radius': radius,
                'type': place_type,
                'key': api_key,
                'language': 'fr'
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                return jsonify({
                    'success': True,
                    'results': result.get('results', [])
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Erreur API Google'
                }), response.status_code
                
        except requests.Timeout:
            return jsonify({
                'success': False,
                'error': 'Timeout - API Google ne répond pas'
            }), 504
        except Exception as e:
            print(f"❌ Erreur proxy nearby search: {e}")
            return jsonify({
                'success': False,
                'error': f'Erreur serveur: {str(e)}'
            }), 500
    
    # ==============================================================================
    # API AGENCE - GÉNÉRATION DE VOYAGES
    # ==============================================================================
    
    @app.route('/api/ai-parse-prompt', methods=['POST'])
    @agency_required
    def api_ai_parse_prompt():
        """
        Parse un prompt en langage naturel avec Gemini AI
        
        POST Body:
            { "prompt": "Voyage en autocar à Rome..." }
        
        Response:
            {
                "success": true,
                "destination": "Rome, Italie",
                "transport_type": "autocar",
                "is_day_trip": false,
                "activities": ["Colisée", "Vatican"],
                "price": 100,
                ...
            }
        """
        from services.ai_assistant import parse_prompt
        
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Veuillez décrire votre voyage'
            }), 400
        
        # Récupérer la clé Gemini de l'agence
        gemini_api_key = get_google_api_key()
        
        if not gemini_api_key:
            return jsonify({
                'success': False,
                'error': 'Clé API Gemini non configurée pour votre agence'
            }), 500
        
        try:
            # Parser le prompt avec l'IA
            parsed_data = parse_prompt(prompt, gemini_api_key)
            
            if not parsed_data.get('success', False):
                return jsonify({
                    'success': False,
                    'error': parsed_data.get('error', 'Erreur de parsing')
                }), 400
            
            return jsonify(parsed_data)
            
        except Exception as e:
            print(f"❌ Erreur API Parse Prompt: {e}")
            return jsonify({
                'success': False,
                'error': f'Erreur serveur: {str(e)}'
            }), 500
    
    @app.route('/api/generate-preview', methods=['POST'])
    @agency_required
    def api_generate_preview():
        """
        Génère la prévisualisation d'un voyage avec appels API externes
        
        POST Body:
            { wizard_data complètes }
        
        Response:
            {
                "success": true,
                "api_data": {
                    "photos": [...],
                    "videos": [...],
                    "reviews": {...},
                    "attractions": {...}
                },
                "form_data": {...},
                "margin": 123,
                "savings": 456
            }
        """
        
        data = request.get_json()
        
        # Vérifier le quota AVANT de générer
        if not check_generation_quota(g.user, g.agency):
            return jsonify({
                'success': False,
                'error': 'Quota de génération dépassé. Réessayez demain ou contactez votre administrateur.'
            }), 429
        
        try:
            # TODO: Implémenter l'appel à services/api_gatherer.py
            # Pour l'instant, retourner des données de test
            
            # Calculer les marges
            form_data = data
            hotel_b2b = float(form_data.get('hotel_b2b_price', 0))
            flight = float(form_data.get('flight_price', 0))
            transfer = float(form_data.get('transfer_cost', 0))
            car = float(form_data.get('car_rental_cost', 0))
            surcharge = float(form_data.get('surcharge_cost', 0))
            pack_price = float(form_data.get('pack_price', 0))
            hotel_b2c = float(form_data.get('hotel_b2c_price', 0))
            
            total_b2b = hotel_b2b + flight + transfer + car + surcharge
            total_b2c = hotel_b2c + flight + transfer + car + surcharge
            
            margin = pack_price - total_b2b
            savings = total_b2c - pack_price
            
            # Incrémenter les compteurs
            increment_generation_counters(g.user, g.agency)
            
            # Réponse (temporaire - à enrichir avec vraies APIs)
            result = {
                'success': True,
                'api_data': {
                    'photos': [
                        {'url': 'https://via.placeholder.com/800x600?text=Photo+1'},
                        {'url': 'https://via.placeholder.com/800x600?text=Photo+2'},
                        {'url': 'https://via.placeholder.com/800x600?text=Photo+3'}
                    ],
                    'videos': [
                        {'id': 'dQw4w9WgXcQ', 'title': 'Visite guidée'}
                    ],
                    'total_reviews': 1250,
                    'average_rating': 4.5,
                    'attractions': {
                        'nearby': ['Attraction 1', 'Attraction 2', 'Attraction 3']
                    }
                },
                'form_data': form_data,
                'margin': int(margin),
                'savings': int(savings)
            }
            
            return jsonify(result)
            
        except Exception as e:
            print(f"❌ Erreur Generate Preview: {e}")
            return jsonify({
                'success': False,
                'error': f'Erreur lors de la génération: {str(e)}'
            }), 500
    
    @app.route('/api/render-html-preview', methods=['POST'])
    @agency_required
    def api_render_html_preview():
        """
        Génère le HTML final de la fiche de voyage
        
        POST Body:
            { generatedData complet }
        
        Response:
            HTML complet (string)
        """
        
        data = request.get_json()
        
        try:
            # TODO: Implémenter services/template_engine.py
            # Pour l'instant, retourner un HTML simple
            
            form_data = data.get('form_data', {})
            api_data = data.get('api_data', {})
            
            is_day_trip = form_data.get('is_day_trip', False)
            
            # HTML basique (à remplacer par vrai template)
            html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{form_data.get('hotel_name', 'Voyage')} - {form_data.get('destination', '')}</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: {g.agency.primary_color}; }}
            .photos {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }}
            .photos img {{ width: 100%; height: 200px; object-fit: cover; }}
            .info {{ margin: 20px 0; }}
            .price {{ font-size: 2em; color: {g.agency.primary_color}; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>{'Excursion' if is_day_trip else 'Séjour'} à {form_data.get('destination', '')}</h1>
        
        {'<h2>' + form_data.get('hotel_name', '') + '</h2>' if not is_day_trip else ''}
        
        <div class="photos">
            {''.join([f'<img src="{photo["url"]}" alt="Photo">' for photo in api_data.get('photos', [])[:3]])}
        </div>
        
        <div class="info">
            <p><strong>Transport:</strong> {form_data.get('transport_type', 'Non spécifié')}</p>
            {'<p><strong>Dates:</strong> ' + form_data.get('date_start', '') + ' au ' + form_data.get('date_end', '') + '</p>' if not is_day_trip else ''}
            {'<p><strong>Horaires:</strong> Départ ' + form_data.get('departure_time', '') + ' - Retour ' + form_data.get('return_time', '') + '</p>' if is_day_trip else ''}
        </div>
        
        <div class="price">
            {form_data.get('pack_price', 0)} € {'par personne' if not is_day_trip else ''}
        </div>
        
        <p><strong>Contact:</strong> {g.agency.contact_email} - {g.agency.contact_phone}</p>
    </body>
    </html>
    """
            
            return html
            
        except Exception as e:
            print(f"❌ Erreur Render HTML: {e}")
            return f"<html><body><h1>Erreur: {str(e)}</h1></body></html>", 500
    
    # ==============================================================================
    # API AGENCE - CRUD VOYAGES
    # ==============================================================================
    
    @app.route('/api/trips', methods=['GET', 'POST'])
    @agency_required
    def api_trips():
        """
        GET: Liste des voyages de l'agence
        POST: Créer/sauvegarder un nouveau voyage
        """
        
        if request.method == 'GET':
            # Liste des voyages selon le rôle
            if g.user.role == 'agency_admin':
                trips = Trip.query.filter_by(agency_id=g.agency.id).all()
            else:
                trips = Trip.query.filter_by(
                    agency_id=g.agency.id,
                    user_id=g.user.id
                ).all()
            
            return jsonify([trip.to_dict() for trip in trips])
        
        elif request.method == 'POST':
            data = request.get_json()
            
            try:
                # Créer le client si nécessaire
                client_id = None
                if data.get('status') == 'assigned':
                    if data.get('form_data', {}).get('client_id'):
                        # Client existant
                        client_id = data['form_data']['client_id']
                    else:
                        # Nouveau client
                        new_client = Client(
                            agency_id=g.agency.id,
                            first_name=data.get('client_first_name', ''),
                            last_name=data.get('client_last_name', ''),
                            email=data.get('client_email', ''),
                            phone=data.get('client_phone', '')
                        )
                        db.session.add(new_client)
                        db.session.flush()
                        client_id = new_client.id
                
                # Créer le voyage
                form_data = data.get('form_data', {})
                
                new_trip = Trip(
                    agency_id=g.agency.id,
                    user_id=g.user.id,
                    client_id=client_id,
                    full_data_json=json.dumps(data),
                    hotel_name=form_data.get('hotel_name', ''),
                    destination=form_data.get('destination', ''),
                    price=int(form_data.get('pack_price', 0)),
                    status=data.get('status', 'proposed'),
                    is_day_trip=form_data.get('is_day_trip', False),
                    transport_type=form_data.get('transport_type'),
                    bus_departure_address=form_data.get('bus_departure_address'),
                    travel_duration_minutes=calculate_duration_minutes(data),
                    departure_time=form_data.get('departure_time'),
                    return_time=form_data.get('return_time'),
                    is_ultra_budget=form_data.get('is_ultra_budget', False)
                )
                
                if data.get('status') == 'assigned':
                    new_trip.assigned_at = datetime.utcnow()
                
                db.session.add(new_trip)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Voyage enregistré avec succès',
                    'trip': new_trip.to_dict()
                })
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erreur sauvegarde voyage: {e}")
                return jsonify({
                    'success': False,
                    'message': f'Erreur lors de la sauvegarde: {str(e)}'
                }), 500
    
    # ==============================================================================
    # API AGENCE - CRUD CLIENTS
    # ==============================================================================
    
    @app.route('/api/clients', methods=['GET', 'POST'])
    @agency_required
    def api_clients():
        """
        GET: Liste des clients de l'agence
        POST: Créer un nouveau client
        """
        
        # Vérifier les permissions
        if g.user.role not in ['agency_admin', 'seller']:
            return jsonify({
                'success': False,
                'error': 'Accès non autorisé'
            }), 403
        
        if request.method == 'GET':
            clients = Client.query.filter_by(agency_id=g.agency.id).order_by(
                Client.created_at.desc()
            ).all()
            return jsonify([client.to_dict() for client in clients])
        
        elif request.method == 'POST':
            data = request.get_json()
            
            try:
                new_client = Client(
                    agency_id=g.agency.id,
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    email=data['email'],
                    phone=data.get('phone', ''),
                    address=data.get('address', '')
                )
                
                db.session.add(new_client)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Client créé avec succès',
                    'client': new_client.to_dict()
                })
                
            except Exception as e:
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'message': f'Erreur: {str(e)}'
                }), 500
    
    # ==============================================================================
    # API AGENCE - UTILITAIRES
    # ==============================================================================
    
    @app.route('/api/ai-generate-program', methods=['POST'])
    @agency_required
    def api_ai_generate_program():
        """
        Génère un programme horaire pour une excursion d'un jour
        
        POST Body:
            {
                "destination": "Rome",
                "activities": ["Colisée", "Vatican"],
                "departure_time": "08:00",
                "return_time": "20:00",
                "departure_address": "Bruxelles"
            }
        
        Response:
            {
                "success": true,
                "program": [
                    {"time": "08:00", "activity": "Départ"},
                    ...
                ]
            }
        """
        from services.ai_assistant import generate_program
        
        data = request.get_json()
        
        gemini_api_key = get_google_api_key()
        
        if not gemini_api_key:
            return jsonify({
                'success': False,
                'error': 'Clé API non configurée'
            }), 500
        
        try:
            program = generate_program(
                destination=data['destination'],
                activities=data.get('activities', []),
                departure_time=data.get('departure_time', '08:00'),
                return_time=data.get('return_time', '20:00'),
                gemini_api_key=gemini_api_key,
                departure_address=data.get('departure_address', 'Bruxelles')
            )
            
            return jsonify({
                'success': True,
                'program': program
            })
            
        except Exception as e:
            print(f"❌ Erreur génération programme: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
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