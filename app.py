# app.py - Application Flask SaaS Multi-Agences Odyssée
import os
import json
import requests
import logging
from datetime import datetime, date, timedelta
from functools import wraps
import zipfile
from io import BytesIO

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, g, abort, make_response, send_file
from flask_migrate import Migrate
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_babel import Babel
from flask_wtf.csrf import CSRFProtect
from flask_session import Session # NOUVEAU
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO, emit, join_room, leave_room
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

# Import optionnel de WeasyPrint (nécessite des bibliothèques système)
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    logging.warning(f"WeasyPrint non disponible: {e}. La génération de PDF sera désactivée.")
    HTML = None
    WEASYPRINT_AVAILABLE = False
from pydantic import ValidationError
from sqlalchemy.orm import joinedload, selectinload

# Import des modèles et configuration
from models import db, Agency, User, Client, Trip, Invoice, TripNote, ActivityLog, SocialMediaCampaign, SocialMediaTemplate, ClientInteraction
from config import get_config
from utils.crypto import init_crypto, decrypt_config, decrypt_api_key

# ==============================================================================
# IMPORTS DES SCHÉMAS DE VALIDATION
# IMPORTS DES SERVICES (avec gestion d'erreurs)
# ==============================================================================

# Import des services - avec gestion d'erreur granulaire pour identifier les problèmes
SERVICES_AVAILABLE = True

try:
    from services.mailer import send_manual_payment_email
except ImportError as e:
    logging.warning(f"Service mailer non disponible: {e}")
    send_manual_payment_email = None

try:
    from services.payment import create_stripe_payment_link
except ImportError as e:
    logging.warning(f"Service payment non disponible: {e}")
    create_stripe_payment_link = None

try:
    from services.publication import publish_via_ftp
except ImportError as e:
    logging.warning(f"Service publication non disponible: {e}")
    publish_via_ftp = None

try:
    from services.template_engine import render_trip_template
except ImportError as e:
    logging.warning(f"Service template_engine non disponible: {e}")
    render_trip_template = None

try:
    from services.ai_assistant import parse_prompt, generate_program
except ImportError as e:
    logging.warning(f"Service ai_assistant non disponible: {e}")
    parse_prompt = None
    generate_program = None

try:
    from services.social_media_generator import SocialMediaGenerator
except ImportError as e:
    logging.warning(f"Service social_media_generator non disponible: {e}")
    SocialMediaGenerator = None

try:
    from services.api_gatherer import gather_trip_data
except ImportError as e:
    logging.error(f"⚠️ ERREUR CRITIQUE - Service api_gatherer non disponible: {e}")
    gather_trip_data = None
    SERVICES_AVAILABLE = False

try:
    from schemas import AgencyCreateSchema, AgencyUpdateSchema, UserCreateSchema, UserUpdateSchema
except ImportError:
    logging.warning("Le fichier schemas.py est manquant. La validation des données sera désactivée.", exc_info=True)
    AgencyCreateSchema, AgencyUpdateSchema, UserCreateSchema, UserUpdateSchema = None, None, None, None

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
    
    # Initialiser Flask-Session (doit être fait AVANT les autres extensions qui utilisent la session)
    Session(app)
    
    # Initialiser les extensions
    db.init_app(app)
    Migrate(app, db)
    mail = Mail(app)
    CORS(app)
    bcrypt = Bcrypt(app)
    csrf = CSRFProtect(app)
    
    # Configuration CSRF pour accepter le header X-CSRFToken
    app.config['WTF_CSRF_CHECK_DEFAULT'] = True
    app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken']
    
    babel = Babel(app)
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=app.config.get('REDIS_URL') or "memory://",
        strategy="moving-window"
    )
    
    # Initialiser le système de chiffrement
    init_crypto(app.config['MASTER_ENCRYPTION_KEY'])
    
    # Initialiser SocketIO pour les notifications temps réel
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # ==============================================================================
    # FILTRES JINJA2 PERSONNALISÉS
    # ==============================================================================
    
    @app.template_filter('format_date')
    def format_date_filter(date_value, format_type='medium'):
        """
        Filtre Jinja2 pour formater les dates.
        
        Args:
            date_value: datetime object ou None
            format_type: 'short', 'medium', 'long', 'full'
        
        Returns:
            str: Date formatée en français
        """
        if not date_value:
            return ''
        
        if isinstance(date_value, str):
            # Si c'est déjà une chaîne, essayer de la parser
            try:
                from dateutil import parser
                date_value = parser.parse(date_value)
            except:
                return date_value
        
        # Formats selon le type demandé
        if format_type == 'short':
            # Format court: 15/10/2025
            return date_value.strftime('%d/%m/%Y')
        elif format_type == 'medium':
            # Format moyen: 15 oct. 2025
            months = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin',
                     'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']
            return f"{date_value.day} {months[date_value.month - 1]} {date_value.year}"
        elif format_type == 'long':
            # Format long: 15 octobre 2025
            months = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                     'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
            return f"{date_value.day} {months[date_value.month - 1]} {date_value.year}"
        elif format_type == 'full':
            # Format complet avec heure: 15 octobre 2025 à 12:50
            months = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                     'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
            return f"{date_value.day} {months[date_value.month - 1]} {date_value.year} à {date_value.strftime('%H:%M')}"
        else:
            # Par défaut: format court
            return date_value.strftime('%d/%m/%Y')
    
    # ==============================================================================
    # CONFIGURATION DE BABEL (LOCALISATION)
    # ==============================================================================
    # Note: Flask-Babel 4.0 configuration simplifiée
    # Pour l'instant, on utilise les valeurs par défaut (français)

    # ==============================================================================
    # CONFIGURATION DES LOGS
    # ==============================================================================
    if not app.debug and not app.testing:
        # En production, on log dans un fichier
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/odyssee.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('🚀 Démarrage de l\'application Odyssée')
    
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
                'youtube_api_key': app.config.get('YOUTUBE_API_KEY')  # Clé YouTube globale si disponible
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

    def check_and_increment_quota(user_id, agency_id):
        """
        Vérifie et incrémente les quotas de manière atomique pour éviter les race conditions.
        Utilise un verrou `FOR UPDATE` sur les lignes utilisateur et agence.
        
        Returns:
            (bool, str): (True, "OK") si le quota est bon, (False, "message d'erreur") sinon.
        """
        try:
            # Verrouiller les lignes pour la mise à jour afin d'éviter les race conditions
            user = db.session.query(User).filter_by(id=user_id).with_for_update().one()
            agency = db.session.query(Agency).filter_by(id=agency_id).with_for_update().one()

            today = date.today()

            # 1. Réinitialiser les compteurs si nécessaire
            if user.last_generation_date != today:
                user.generation_count = 0
                user.last_generation_date = today

            if agency.usage_reset_date < today:
                agency.current_month_usage = 0
                agency.usage_reset_date = (today.replace(day=1) + timedelta(days=32)).replace(day=1)

            # 2. Vérifier les quotas
            if user.generation_count >= user.daily_generation_limit:
                return False, "Votre quota de génération quotidien est atteint."
            if agency.current_month_usage >= agency.monthly_generation_limit:
                return False, "Le quota de génération mensuel de l'agence est atteint."

            # 3. Incrémenter les compteurs
            user.generation_count += 1
            agency.current_month_usage += 1
            
            db.session.commit()
            return True, "OK"

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur lors de la vérification du quota : {e}", exc_info=True)
            return False, "Erreur serveur lors de la vérification du quota."

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
    
    # NOUVEAU : Helper pour logger les activités
    def log_activity(action: str, user_id: int, agency_id: int, trip_id: int = None, details: str = None):
        """Enregistre une activité dans le journal de l'agence."""
        try:
            activity = ActivityLog(
                action=action,
                user_id=user_id,
                agency_id=agency_id,
                trip_id=trip_id,
                details=details
            )
            db.session.add(activity)
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Erreur lors de la journalisation de l'activité: {e}", exc_info=True)
            db.session.rollback()
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
    
    def get_gemini_api_key():
        """
        Récupère la clé Gemini API pour l'IA (agence en priorité, sinon globale)
        
        Returns:
            str: Clé API Gemini ou None
        """
        # Priorité 1 : Clé de l'agence (chiffrée en BDD)
        if hasattr(g, 'agency_config') and g.agency_config.get('google_api_key'):
            return g.agency_config['google_api_key']
        
        # Priorité 2 : Clé globale depuis .env (peut être la même que Google Places)
        return app.config.get('GOOGLE_PLACES_API_KEY') or app.config.get('GOOGLE_GEMINI_API_KEY')
    
    # ==============================================================================
    # COMMANDE CLI - INITIALISATION
    # ==============================================================================
    
    @app.cli.command("init-db")
    def init_db_command():
        """Initialise la base de données et crée le super-admin."""
        with app.app_context():
            # Créer toutes les tables
            db.create_all()
            app.logger.info("Base de données et tables créées avec la commande init-db.")
            
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
                
                app.logger.info(f"Super-admin créé : {super_admin.username}")
                app.logger.info(f"   Email: {super_admin.email}")
                app.logger.info(f"   Mot de passe: {app.config['SUPER_ADMIN_PASSWORD']}")
            else:
                app.logger.info(f"Super-admin existe déjà : {super_admin.username}")
    
    # ==============================================================================
    # ROUTES D'AUTHENTIFICATION
    # ==============================================================================
    
    @app.route('/login', methods=['GET', 'POST'])
    @limiter.limit("10 per minute") # Limite stricte pour éviter le brute-force
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
            try:
                # 1. Valider les données d'entrée avec Pydantic
                validated_data = AgencyCreateSchema(**request.get_json())
                data = validated_data.dict() # Convertir en dictionnaire

                # 2. Vérifier les contraintes métier (unicité)
                existing = Agency.query.filter_by(subdomain=data['subdomain']).first()
                if existing:
                    return jsonify({'success': False, 'message': 'Ce sous-domaine existe déjà'}), 400

                # 3. Créer l'objet SQLAlchemy
                new_agency = Agency(
                    name=data['name'],
                    subdomain=data['subdomain'],
                    contact_email=data['contact_email'],
                    logo_url=str(data['logo_url']) if data['logo_url'] else None, # Pydantic renvoie un objet URL
                    primary_color=data['primary_color'],
                    template_name=data['template_name'],
                    contact_phone=data['contact_phone'],
                    contact_address=data['contact_address'],
                    manual_payment_email_template=data['manual_payment_email_template'],
                    website_url=str(data['website_url']) if data['website_url'] else None,
                    subscription_tier=data['subscription_tier'],
                    monthly_generation_limit=data['monthly_generation_limit']
                )

                from utils.crypto import encrypt_api_key, encrypt_config
                
                # Chiffrer les configs si fournies
                if data['google_api_key']:
                    new_agency.google_api_key_encrypted = encrypt_api_key(data['google_api_key'])
                
                if data['stripe_api_key']:
                    new_agency.stripe_api_key_encrypted = encrypt_api_key(data['stripe_api_key'])
                
                if data['mail_config']:
                    new_agency.mail_config_encrypted = encrypt_config(data['mail_config'])

                if data['ftp_config']:
                    new_agency.ftp_config_encrypted = encrypt_config(data['ftp_config'])
                
                db.session.add(new_agency)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Agence créée avec succès',
                    'agency': new_agency.to_dict()
                })
                
            except ValidationError as e:
                # Erreur de validation Pydantic
                return jsonify({'success': False, 'message': 'Données invalides', 'errors': e.errors()}), 400
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erreur lors de la création d'agence: {e}", exc_info=True)
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
            try:
                # Prétraiter les données pour convertir les chaînes vides en None
                raw_data = request.get_json()
                
                # Convertir les chaînes vides en None pour les champs optionnels
                for field in ['logo_url', 'website_url', 'google_api_key', 'stripe_api_key', 
                             'contact_phone', 'contact_address', 'manual_payment_email_template']:
                    if field in raw_data and raw_data[field] == '':
                        raw_data[field] = None
                
                # Convertir les objets vides en None pour les configs
                for config_field in ['ftp_config', 'mail_config']:
                    if config_field in raw_data and isinstance(raw_data[config_field], dict):
                        # Si le dict est vide ou ne contient que des valeurs vides, le mettre à None
                        if not raw_data[config_field] or all(not v for v in raw_data[config_field].values()):
                            raw_data[config_field] = None
                
                # 1. Valider les données d'entrée avec Pydantic
                validated_data = AgencyUpdateSchema(**raw_data)
                # Obtenir uniquement les champs qui ont été fournis dans la requête
                update_data = validated_data.dict(exclude_unset=True)

                # 2. Appliquer les mises à jour
                from utils.crypto import encrypt_api_key, encrypt_config

                for key, value in update_data.items():
                    # Logique métier spécifique pour certains champs
                    if key == 'subdomain' and value != agency.subdomain:
                        existing = Agency.query.filter_by(subdomain=value).first()
                        if existing:
                            return jsonify({'success': False, 'message': 'Ce sous-domaine existe déjà'}), 400
                        agency.subdomain = value
                    # Champs chiffrés
                    elif key == 'google_api_key':
                        agency.google_api_key_encrypted = encrypt_api_key(value) if value else None
                    elif key == 'stripe_api_key':
                        agency.stripe_api_key_encrypted = encrypt_api_key(value) if value else None
                    elif key == 'mail_config':
                        agency.mail_config_encrypted = encrypt_config(value) if value else None
                    elif key == 'ftp_config':
                        agency.ftp_config_encrypted = encrypt_config(value) if value else None
                    # Champs URL qui sont des objets Pydantic
                    elif key in ['logo_url', 'website_url'] and value is not None:
                        setattr(agency, key, str(value))
                    # Tous les autres champs
                    else:
                        setattr(agency, key, value)

                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Agence modifiée avec succès',
                    'agency': agency.to_dict()
                })
                
            except ValidationError as e:
                return jsonify({'success': False, 'message': 'Données invalides', 'errors': e.errors()}), 400
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erreur lors de la mise à jour de l'agence {agency_id}: {e}", exc_info=True)
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
                app.logger.error(f"Erreur lors de la suppression de l'agence {agency_id}: {e}", exc_info=True)
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
                # 1. Valider les données
                validated_data = UserCreateSchema(**request.get_json())
                data = validated_data.dict()

                # 2. Vérifier les contraintes d'unicité
                if User.query.filter_by(username=data['username']).first():
                    return jsonify({'success': False, 'message': 'Ce nom d\'utilisateur existe déjà'}), 400
                if User.query.filter_by(email=data['email']).first():
                    return jsonify({'success': False, 'message': 'Cet email existe déjà'}), 400

                # 3. Créer l'objet
                # Hash du mot de passe
                hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
                
                new_user = User(
                    agency_id=agency_id,
                    username=data['username'],
                    password=hashed_password,
                    pseudo=data['pseudo'],
                    email=data['email'],
                    phone=data.get('phone'),
                    role=data['role'],
                    margin_percentage=data['margin_percentage'],
                    daily_generation_limit=data['daily_generation_limit'],
                    is_active=True
                )
                
                db.session.add(new_user)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Utilisateur créé avec succès',
                    'user': new_user.to_dict()
                })
                
            except ValidationError as e:
                return jsonify({'success': False, 'message': 'Données invalides', 'errors': e.errors()}), 400
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erreur lors de la création de l'utilisateur pour l'agence {agency_id}: {e}", exc_info=True)
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
            try:
                # 1. Valider les données
                validated_data = UserUpdateSchema(**request.get_json())
                update_data = validated_data.dict(exclude_unset=True)

                # 2. Appliquer les mises à jour
                for key, value in update_data.items():
                    if key == 'username' and value != user.username:
                        if User.query.filter_by(username=value).first():
                            return jsonify({'success': False, 'message': 'Ce nom d\'utilisateur existe déjà'}), 400
                        user.username = value
                    elif key == 'email' and value != user.email:
                        if User.query.filter_by(email=value).first():
                            return jsonify({'success': False, 'message': 'Cet email existe déjà'}), 400
                        user.email = value
                    elif key == 'password':
                        if value and value.strip(): # S'assurer que le mot de passe n'est pas vide
                            user.password = bcrypt.generate_password_hash(value).decode('utf-8')
                    else:
                        setattr(user, key, value)
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Utilisateur modifié avec succès',
                    'user': user.to_dict()
                })
                

            except ValidationError as e:
                return jsonify({'success': False, 'message': 'Données invalides', 'errors': e.errors()}), 400
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erreur lors de la mise à jour de l'utilisateur {user_id}: {e}", exc_info=True)
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
                app.logger.error(f"Erreur lors de la suppression de l'utilisateur {user_id}: {e}", exc_info=True)
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
        
        # Récupérer les dernières activités
        if g.user.role == 'agency_admin':
            activities = ActivityLog.query.filter_by(agency_id=g.agency.id).order_by(ActivityLog.created_at.desc()).limit(10).all()
        else:
            # Le vendeur ne voit que ses activités
            activities = ActivityLog.query.filter_by(user_id=g.user.id).order_by(ActivityLog.created_at.desc()).limit(10).all()


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
        return render_template('agency/dashboard.html', stats=stats, activities=activities)
    
    @app.route('/agency/generate')
    @agency_required
    def generate_trip():
        """Page de génération de voyage avec Wizard IA"""
        google_api_key = get_google_api_key()
        if not google_api_key:
            return render_template('error.html', 
                                 message='Aucune clé Google API configurée. Contactez votre administrateur.')
        
        # Vérifier le quota
        # La vérification se fait maintenant au moment de la génération via l'API,
        # pour ne pas bloquer l'accès à la page si le quota est plein.
        
        # ⚠️ SÉCURITÉ : On ne passe PLUS la clé au template
        # Les appels Google se feront via les routes proxy
        return render_template('agency/generate.html',
                             user_margin=g.user.margin_percentage)
    
    @app.route('/agency/trips')
    @agency_required
    def trips_list():
        """Liste des voyages de l'agence"""
        page = request.args.get('page', 1, type=int)
        per_page = 15 # Nombre d'éléments par page
        
        # Récupérer les paramètres de filtrage
        status_filter = request.args.get('status', '').strip()
        type_filter = request.args.get('type', '').strip()
        search_query = request.args.get('search', '').strip()
        
        # Selon le rôle, filtrer les voyages
        if g.user.role == 'agency_admin':
            query = Trip.query.options(
                joinedload(Trip.user), 
                joinedload(Trip.client)
            ).filter_by(agency_id=g.agency.id)
        else:
            # Seller voit seulement ses voyages
            query = Trip.query.options(
                joinedload(Trip.user), 
                joinedload(Trip.client)
            ).filter_by(agency_id=g.agency.id, user_id=g.user.id)
        
        # Appliquer les filtres
        if status_filter:
            query = query.filter(Trip.status == status_filter)
        
        if type_filter:
            if type_filter == 'day_trip':
                query = query.filter(Trip.is_day_trip == True)
            elif type_filter == 'sejour':
                query = query.filter(Trip.is_day_trip == False)
        
        if search_query:
            # Recherche multi-critères dans tous les champs pertinents
            search_pattern = f"%{search_query}%"
            
            # Joindre avec la table Client pour pouvoir chercher dans les noms des clients
            query = query.outerjoin(Client, Trip.client_id == Client.id)
            
            query = query.filter(
                (Trip.destination.ilike(search_pattern)) | 
                (Trip.hotel_name.ilike(search_pattern)) |
                (Trip.transport_type.ilike(search_pattern)) |
                (Trip.bus_departure_address.ilike(search_pattern)) |
                (Client.first_name.ilike(search_pattern)) |
                (Client.last_name.ilike(search_pattern)) |
                ((Client.first_name + ' ' + Client.last_name).ilike(search_pattern)) |
                (Client.email.ilike(search_pattern))
            )
        
        # Trier par date de création (plus récent en premier)
        query = query.order_by(Trip.created_at.desc())
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        trips = pagination.items
        
        return render_template('agency/trips.html', trips=trips, pagination=pagination)
    
    @app.route('/agency/clients')
    @agency_required
    def clients_list():
        """Gestion des clients de l'agence"""
        from sqlalchemy import or_
        
        # Seuls les admins ont accès à la liste complète des clients
        if g.user.role != 'agency_admin':
            abort(403, "Accès réservé aux administrateurs d'agence")
        
        page = request.args.get('page', 1, type=int)
        search_term = request.args.get('search', '')
        per_page = 12 # 12 clients par page pour une grille 3x4

        query = Client.query.filter_by(agency_id=g.agency.id)

        if search_term:
            search_filter = f"%{search_term}%"
            query = query.filter(or_(
                (Client.first_name + ' ' + Client.last_name).ilike(search_filter),
                Client.email.ilike(search_filter)
            ))

        pagination = query.order_by(Client.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        clients = pagination.items
        
        return render_template('agency/clients.html', clients=clients, pagination=pagination)

    # NOUVEAU : Page de détail d'un voyage
    @app.route('/agency/trips/<int:trip_id>')
    @agency_required
    def trip_detail(trip_id):
        """Affiche la page de détail d'un voyage."""
        # Optimisation : charger toutes les relations nécessaires en une seule fois
        trip = Trip.query.options(
            joinedload(Trip.user),
            joinedload(Trip.client),
            selectinload(Trip.notes).joinedload(TripNote.author), # Charger les notes ET leurs auteurs
            selectinload(Trip.invoices)
        ).filter_by(id=trip_id).first_or_404()

        # Vérifier que le voyage appartient bien à l'agence
        if trip.agency_id != g.agency.id:
            abort(403)

        # Si l'utilisateur est un vendeur, vérifier qu'il a créé le voyage
        if g.user.role == 'seller' and trip.user_id != g.user.id:
            abort(403, "Vous n'avez pas la permission de voir ce voyage.")

        # Charger les données JSON pour un affichage complet
        full_data = json.loads(trip.full_data_json)
        
        # Calculer la date minimale pour le solde (demain)
        min_balance_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        return render_template('agency/trip_detail.html', trip=trip, full_data=full_data, min_balance_date=min_balance_date)

    # NOUVEAU : Page pour modifier un voyage
    @app.route('/agency/trips/<int:trip_id>/edit')
    @agency_required
    def edit_trip(trip_id):
        """Affiche le formulaire de modification d'un voyage."""
        trip = Trip.query.get_or_404(trip_id)

        # Sécurité : Vérifier l'appartenance
        if trip.agency_id != g.agency.id:
            abort(403)
        if g.user.role == 'seller' and trip.user_id != g.user.id:
            abort(403)

        # On ne peut modifier que les voyages non vendus
        if trip.status == 'sold':
            return render_template('error.html', message="Impossible de modifier un voyage qui a été vendu.")

        full_data = json.loads(trip.full_data_json)
        return render_template('agency/edit_trip.html', trip=trip, full_data=full_data)

    # NOUVEAU : Route pour voir la fiche HTML générée
    @app.route('/agency/trips/<int:trip_id>/preview')
    @agency_required
    def preview_trip_html(trip_id):
        """Affiche la fiche de présentation du voyage en HTML."""
        trip = Trip.query.get_or_404(trip_id)

        # Sécurité : Vérifier que le voyage appartient bien à l'agence
        if trip.agency_id != g.agency.id:
            abort(403, "Accès non autorisé à ce voyage.")

        # Sécurité : Vendeur ne peut voir que ses propres voyages
        if g.user.role == 'seller' and trip.user_id != g.user.id:
            abort(403, "Vous n'avez pas la permission de voir ce voyage.")

        # Charger les données complètes du voyage
        full_data = json.loads(trip.full_data_json)
        
        # Déterminer le type de template
        template_type = 'day_trip' if trip.is_day_trip else 'standard'
        
        # Rendre le template HTML de la fiche de voyage
        html_string = render_trip_template(
            data=full_data,
            template_type=template_type,
            agency_style=g.agency.template_name,
            agency_config=g.agency.to_dict()
        )

        return html_string

    # NOUVEAU : Route pour générer le PDF de la fiche de présentation du voyage
    @app.route('/agency/trips/<int:trip_id>/pdf')
    @agency_required
    def generate_trip_pdf(trip_id):
        """Génère et retourne le PDF de la fiche de présentation d'un voyage."""
        if not WEASYPRINT_AVAILABLE:
            return render_template('error.html', 
                message="La génération de PDF n'est pas disponible sur ce serveur. Contactez l'administrateur."), 503
        
        trip = Trip.query.get_or_404(trip_id)

        # Sécurité : Vérifier que le voyage appartient bien à l'agence
        if trip.agency_id != g.agency.id:
            abort(403, "Accès non autorisé à ce voyage.")

        # Sécurité : Vendeur ne peut voir que ses propres voyages
        if g.user.role == 'seller' and trip.user_id != g.user.id:
            abort(403, "Vous n'avez pas la permission de voir ce voyage.")

        # Charger les données complètes du voyage
        full_data = json.loads(trip.full_data_json)
        
        # Déterminer le type de template
        template_type = 'day_trip' if trip.is_day_trip else 'standard'
        
        # Rendre le template HTML de la fiche de voyage
        html_string = render_trip_template(
            data=full_data,
            template_type=template_type,
            agency_style=g.agency.template_name,
            agency_config=g.agency.to_dict()
        )

        try:
            pdf = HTML(string=html_string).write_pdf()
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename=voyage-{trip.destination.replace(" ", "-")}.pdf'
            return response
        except Exception as e:
            app.logger.error(f"Erreur génération PDF: {e}", exc_info=True)
            return render_template('error.html', 
                message="Erreur lors de la génération du PDF. Veuillez contacter l'administrateur."), 500

    # NOUVEAU : Route pour générer le PDF d'une facture
    @app.route('/agency/invoices/<int:invoice_id>/pdf')
    @agency_required
    def generate_invoice_pdf(invoice_id):
        """Génère et retourne le PDF d'une facture."""
        if not WEASYPRINT_AVAILABLE:
            return render_template('error.html', 
                message="La génération de PDF n'est pas disponible sur ce serveur. Contactez l'administrateur."), 503
        
        invoice = Invoice.query.get_or_404(invoice_id)
        trip = invoice.trip

        # Sécurité : Vérifier que la facture appartient bien à l'agence
        if trip.agency_id != g.agency.id:
            abort(403, "Accès non autorisé à cette facture.")

        # Sécurité : Vendeur ne peut voir que ses propres factures
        if g.user.role == 'seller' and trip.user_id != g.user.id:
            abort(403, "Vous n'avez pas la permission de voir cette facture.")

        # Rendre le template HTML de la facture
        html_string = render_template(
            'agency/invoice_pdf.html',
            invoice=invoice,
            trip=trip,
            client=trip.client,
            agency=g.agency
        )

        try:
            # Générer le PDF et créer la réponse
            pdf = HTML(string=html_string).write_pdf()
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename={invoice.invoice_number}.pdf'
            return response
        except Exception as e:
            app.logger.error(f"Erreur génération PDF facture: {e}", exc_info=True)
            return render_template('error.html', 
                message="Erreur lors de la génération du PDF. Veuillez contacter l'administrateur."), 500
    
        # Version corrigée
    @app.route('/agency/generate/manual')
    @agency_required
    def generate_trip_manual():
        """Page de génération de voyage avec formulaire manuel complet."""
    
        return render_template('agency/generate_manual.html', 
                               user_margin=g.user.margin_percentage)
    
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
            types = data.get('types', 'establishment')  # Type de lieu à rechercher
            
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
                'key': api_key,
                'language': 'fr'
            }
            
            # Ajouter les types de lieux
            if types:
                params['types'] = types
            
            # Pour les adresses en Belgique, ajouter une restriction de pays
            if types == 'address':
                params['components'] = 'country:be'
            
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
            app.logger.error(f"Erreur proxy autocomplete: {e}", exc_info=True)
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
            app.logger.error(f"Erreur proxy place details: {e}", exc_info=True)
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
            app.logger.error(f"Erreur proxy photos: {e}", exc_info=True)
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
            app.logger.error(f"Erreur proxy nearby search: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Erreur serveur: {str(e)}'
            }), 500
    
    # ==============================================================================
    # API AGENCE - GÉNÉRATION DE VOYAGES
    # ==============================================================================
    
    @app.route('/api/ai-parse-prompt', methods=['POST'])
    @agency_required
    @limiter.limit("60 per hour", key_func=lambda: session.get('user_id'))
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
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Veuillez décrire votre voyage'
            }), 400
        
        # Récupérer la clé Gemini de l'agence
        gemini_api_key = get_gemini_api_key()
        
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
            app.logger.error(f"Erreur API Parse Prompt: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Erreur serveur: {str(e)}'
            }), 500
    
    @app.route('/api/generate-preview', methods=['POST'])
    @agency_required
    @limiter.limit("30 per hour;10 per minute", key_func=lambda: session.get('user_id'))
    def api_generate_preview():
        """
        Génère la prévisualisation d'un voyage avec appels API externes
        
        POST Body:
            { form_data complètes }
        
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
        
        data = request.get_json() or {}
        
        try:
            # Vérifier et incrémenter le quota de manière atomique
            quota_ok, message = check_and_increment_quota(g.user.id, g.agency.id)
            if not quota_ok:
                return jsonify({'success': False, 'error': message}), 429

            # MODIFIÉ : Appel du service réel
            enriched_data = gather_trip_data(data.get('form_data', {}), g.agency_config)
            
            # Le compteur est déjà incrémenté par check_and_increment_quota
            
            return jsonify(enriched_data)
            
        except Exception as e:
            app.logger.error(f"Erreur Generate Preview: {e}", exc_info=True)
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
        data = request.get_json() or {}
        
        try:
            # Déterminer le type de template
            template_type = 'day_trip' if data.get('form_data', {}).get('is_day_trip') else 'standard'
            
            # Générer le HTML avec le template engine
            html = render_trip_template(
                data,
                template_type,
                g.agency.template_name,
                g.agency.to_dict()
            )
            
            return make_response(html)
            
        except Exception as e:
            app.logger.error(f"Erreur Render HTML: {e}", exc_info=True)
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
            page = request.args.get('page', 1, type=int)
            per_page = 20

            # Liste des voyages selon le rôle
            if g.user.role == 'agency_admin':
                query = Trip.query.options(
                    joinedload(Trip.user)
                ).filter_by(agency_id=g.agency.id)
            else:
                query = Trip.query.options(
                    joinedload(Trip.user)
                ).filter_by(agency_id=g.agency.id, user_id=g.user.id)
            
            pagination = query.order_by(Trip.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
            trips = pagination.items
            
            return jsonify({
                'success': True,
                'trips': [trip.to_dict() for trip in trips],
                'pagination': {
                    'total_pages': pagination.pages,
                    'total_items': pagination.total,
                    'current_page': pagination.page,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            
            try:
                client_id = None
                form_data = data.get('form_data', {})
                
                # Gestion du client (existant ou nouveau)
                if form_data.get('client_id'):
                    client_id = int(form_data.get('client_id'))
                elif data.get('client_email'):
                    # Vérifier si un client avec cet email existe déjà pour cette agence
                    existing_client = Client.query.filter_by(
                        agency_id=g.agency.id,
                        email=data.get('client_email')
                    ).first()

                    if existing_client:
                        client_id = existing_client.id
                    else:
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

                # Déterminer le statut
                status = data.get('status', 'proposed')
                assigned_at = datetime.utcnow() if status == 'assigned' else None
                
                # Créer le voyage
                new_trip = Trip(
                    agency_id=g.agency.id,
                    user_id=g.user.id,
                    client_id=client_id,
                    full_data_json=json.dumps(data),
                    hotel_name=form_data.get('hotel_name', 'Voyage sans hôtel'),
                    destination=form_data.get('destination', 'Destination inconnue'),
                    price=int(form_data.get('pack_price', 0)),
                    status=status,
                    is_day_trip=form_data.get('is_day_trip', False),
                    is_ultra_budget=form_data.get('is_ultra_budget', False),
                    assigned_at=assigned_at,
                    # Les champs ci-dessous sont spécifiques aux excursions et seront NULL sinon
                    transport_type=form_data.get('transport_type'),
                    bus_departure_address=form_data.get('bus_departure_address'),
                    travel_duration_minutes=calculate_duration_minutes(data),
                    departure_time=form_data.get('departure_time'),
                    return_time=form_data.get('return_time'),
                )
                
                db.session.add(new_trip)
                db.session.commit()
                
                # Log de l'activité
                log_activity(
                    action='trip_created',
                    user_id=g.user.id,
                    agency_id=g.agency.id,
                    trip_id=new_trip.id,
                    details=f"Voyage vers {new_trip.destination}"
                )

                return jsonify({
                    'success': True,
                    'message': 'Voyage enregistré avec succès',
                    'trip': new_trip.to_dict()
                })
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erreur sauvegarde voyage: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'message': f'Erreur lors de la sauvegarde: {str(e)}'
                }), 500

    # NOUVEAU : Route pour mettre à jour un voyage
    @app.route('/api/trips/<int:trip_id>', methods=['GET', 'PUT', 'DELETE'])
    @agency_required
    def api_trip_detail(trip_id):
        """
        GET: Récupère les détails d'un voyage
        PUT: Met à jour un voyage existant
        DELETE: Supprime un voyage
        """
        trip = Trip.query.get_or_404(trip_id)

        # Sécurité : Vérifier l'appartenance et les permissions
        if trip.agency_id != g.agency.id:
            abort(403)
        if g.user.role == 'seller' and trip.user_id != g.user.id:
            abort(403)
        
        if request.method == 'GET':
            # Retourner les détails complets du voyage avec full_data déjà parsé
            trip_dict = trip.to_dict()
            trip_dict['full_data'] = json.loads(trip.full_data_json)
            return jsonify(trip_dict)
        
        elif request.method == 'DELETE':
            # Supprimer le voyage
            try:
                # Vérifier si le voyage peut être supprimé
                if trip.status == 'sold':
                    return jsonify({
                        'success': False,
                        'message': 'Impossible de supprimer un voyage vendu.'
                    }), 403
                
                db.session.delete(trip)
                db.session.commit()
                
                # Log de l'activité
                log_activity(
                    action='trip_deleted',
                    user_id=g.user.id,
                    agency_id=g.agency.id,
                    details=f"Voyage vers {trip.destination} supprimé"
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Voyage supprimé avec succès'
                })
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erreur lors de la suppression du voyage {trip_id}: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'message': f'Erreur lors de la suppression: {str(e)}'
                }), 500
        
        elif request.method == 'PUT':
            # Mettre à jour le voyage
            if trip.status == 'sold':
                return jsonify({'success': False, 'message': 'Impossible de modifier un voyage vendu.'}), 403

            data = request.get_json() or {}
            form_data = data.get('form_data', {})

            try:
                # Mettre à jour les champs principaux
                trip.hotel_name = form_data.get('hotel_name', trip.hotel_name)
                trip.destination = form_data.get('destination', trip.destination)
                trip.price = int(form_data.get('pack_price', trip.price))
                trip.is_day_trip = form_data.get('is_day_trip', trip.is_day_trip)
                
                # Mettre à jour les champs spécifiques aux excursions
                trip.transport_type = form_data.get('transport_type', trip.transport_type)
                trip.bus_departure_address = form_data.get('bus_departure_address', trip.bus_departure_address)
                trip.travel_duration_minutes = calculate_duration_minutes(data)
                trip.departure_time = form_data.get('departure_time', trip.departure_time)
                trip.return_time = form_data.get('return_time', trip.return_time)

                # Mettre à jour le JSON complet
                # On fusionne les anciennes données avec les nouvelles pour ne rien perdre
                current_full_data = json.loads(trip.full_data_json)
                current_full_data['form_data'].update(form_data)
                trip.full_data_json = json.dumps(current_full_data)

                db.session.commit()

                return jsonify({
                    'success': True,
                    'message': 'Voyage mis à jour avec succès.',
                    'trip': trip.to_dict()
                })

            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erreur mise à jour voyage {trip_id}: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'message': f'Erreur lors de la mise à jour: {str(e)}'
                }), 500

    @app.route('/api/trips/<int:trip_id>/reproduce', methods=['POST'])
    @agency_required
    def api_reproduce_trip(trip_id):
        """Duplique un voyage existant."""
        trip = Trip.query.get_or_404(trip_id)

        # Sécurité : Vérifier l'appartenance et les permissions
        if trip.agency_id != g.agency.id:
            abort(403)
        if g.user.role == 'seller' and trip.user_id != g.user.id:
            abort(403)

        try:
            # Créer une copie du voyage
            new_trip = Trip(
                agency_id=trip.agency_id,
                user_id=g.user.id,  # Le nouveau voyage appartient à l'utilisateur actuel
                client_id=None,  # Pas de client assigné à la copie
                full_data_json=trip.full_data_json,  # Copier toutes les données
                hotel_name=trip.hotel_name,
                destination=trip.destination,
                price=trip.price,
                status='proposed',  # Toujours en statut "proposé"
                is_day_trip=trip.is_day_trip,
                is_ultra_budget=trip.is_ultra_budget,
                transport_type=trip.transport_type,
                bus_departure_address=trip.bus_departure_address,
                travel_duration_minutes=trip.travel_duration_minutes,
                departure_time=trip.departure_time,
                return_time=trip.return_time
            )
            
            db.session.add(new_trip)
            db.session.commit()
            
            # Log de l'activité
            log_activity(
                action='trip_reproduced',
                user_id=g.user.id,
                agency_id=g.agency.id,
                trip_id=new_trip.id,
                details=f"Voyage vers {new_trip.destination} dupliqué depuis le voyage #{trip_id}"
            )
            
            return jsonify({
                'success': True,
                'message': 'Voyage dupliqué avec succès',
                'trip': new_trip.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur lors de la duplication du voyage {trip_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'message': f'Erreur lors de la duplication: {str(e)}'
            }), 500

    @app.route('/api/trips/<int:trip_id>/assign', methods=['POST'])
    @agency_required
    def api_assign_client(trip_id):
        """Assigne un client à un voyage existant."""
        
        trip = Trip.query.get_or_404(trip_id)

        # Vérifier que le voyage appartient bien à l'agence de l'utilisateur
        if trip.agency_id != g.user.agency_id:
            abort(403, "Accès non autorisé à ce voyage.")

        data = request.get_json()
        client_id = data.get('client_id')

        if not client_id:
            return jsonify({'success': False, 'message': 'ID du client manquant.'}), 400

        client = Client.query.get(client_id)
        if not client or client.agency_id != g.user.agency_id:
            return jsonify({'success': False, 'message': 'Client non trouvé ou invalide.'}), 404

        try:
            trip.client_id = client.id
            trip.status = 'assigned'
            trip.assigned_at = datetime.utcnow()
            
            db.session.commit()

            # Log de l'activité
            log_activity(
                action='trip_assigned',
                user_id=g.user.id,
                agency_id=g.agency.id,
                trip_id=trip.id,
                details=f"Assigné à {client.first_name} {client.last_name}"
            )
            
            return jsonify({
                'success': True,
                'message': f'Voyage assigné à {client.first_name} {client.last_name}',
                'trip': trip.to_dict()
            })
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur lors de l'assignation du client au voyage {trip_id}: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500

    # NOUVEAU : Route pour marquer un voyage comme vendu
    @app.route('/api/trips/<int:trip_id>/sell', methods=['POST'])
    @agency_required
    def api_sell_trip(trip_id):
        """Marque un voyage comme vendu."""
        
        trip = Trip.query.get_or_404(trip_id)

        # Vérifier que le voyage appartient bien à l'agence de l'utilisateur
        if trip.agency_id != g.user.agency_id:
            abort(403, "Accès non autorisé à ce voyage.")

        # Seuls les admins ou le vendeur créateur peuvent marquer comme vendu
        if g.user.role != 'agency_admin' and trip.user_id != g.user.id:
            abort(403, "Vous n'avez pas la permission de modifier ce voyage.")

        # Vérifier si une facture existe déjà pour éviter les doublons
        if Invoice.query.filter_by(trip_id=trip.id).first():
            return jsonify({'success': False, 'message': 'Une facture existe déjà pour ce voyage.'}), 409

        try:
            trip.status = 'sold'
            trip.sold_at = datetime.utcnow()
            
            # NOUVEAU : Logique de création de facture
            new_invoice = Invoice(
                trip_id=trip.id,
                # Format simple pour le numéro de facture. On pourra le complexifier plus tard.
                invoice_number=f"FACTURE-{trip.agency_id}-{trip.id}"
            )
            db.session.add(new_invoice)
            
            db.session.commit()

            # Log de l'activité
            log_activity(
                action='trip_sold',
                user_id=g.user.id,
                agency_id=g.agency.id,
                trip_id=trip.id,
                details=f"Vendu pour {trip.price}€"
            )
            
            return jsonify({
                'success': True,
                'message': 'Voyage marqué comme vendu et facture créée avec succès.',
                'trip': trip.to_dict()
            })
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur lors de la vente du voyage {trip_id}: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500

    # NOUVEAU : Route pour ajouter une note à un voyage
    @app.route('/api/trips/<int:trip_id>/notes', methods=['POST'])
    @agency_required
    def api_add_trip_note(trip_id):
        """Ajoute une note interne à un voyage."""
        trip = Trip.query.get_or_404(trip_id)

        # Sécurité : Vérifier que le voyage appartient bien à l'agence
        if trip.agency_id != g.agency.id:
            abort(403)
        # Sécurité : Vendeur ne peut commenter que ses propres voyages
        if g.user.role == 'seller' and trip.user_id != g.user.id:
            abort(403)

        data = request.get_json()
        content = data.get('content')

        if not content or not content.strip():
            return jsonify({'success': False, 'message': 'Le contenu de la note ne peut pas être vide.'}), 400

        try:
            new_note = TripNote(
                content=content,
                trip_id=trip.id,
                user_id=g.user.id
            )
            db.session.add(new_note)
            db.session.commit()

            # Log de l'activité
            log_activity(
                action='note_added',
                user_id=g.user.id,
                agency_id=g.agency.id,
                trip_id=trip.id,
                details=f"Note ajoutée au voyage vers {trip.destination}"
            )
            return jsonify({'success': True, 'note': new_note.to_dict()})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur lors de l'ajout d'une note au voyage {trip_id}: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500

    # NOUVEAU : Route pour publier une fiche de voyage
    @app.route('/api/trips/<int:trip_id>/publish', methods=['POST'])
    @agency_required
    def api_publish_trip(trip_id):
        """Publie la fiche de présentation d'un voyage via FTP."""
        trip = Trip.query.get_or_404(trip_id)

        # Sécurité
        if trip.agency_id != g.agency.id or (g.user.role == 'seller' and trip.user_id != g.user.id):
            abort(403)

        # Vérifier si la configuration FTP existe
        ftp_config = g.agency_config.get('ftp_config')
        if not ftp_config or not ftp_config.get('host'):
            return jsonify({'success': False, 'message': 'La configuration FTP est manquante pour cette agence.'}), 400

        try:            # 1. Générer le HTML de la fiche
            full_data = json.loads(trip.full_data_json)
            template_type = 'day_trip' if trip.is_day_trip else 'standard'
            html_content = render_trip_template(full_data, template_type, g.agency.template_name, g.agency.to_dict())

            # 2. Publier via FTP
            filename = f"voyage-{trip.id}-{trip.destination.lower().replace(' ', '-')}.html"
            success = publish_via_ftp(html_content, filename, ftp_config)

            if not success:
                raise Exception("La publication FTP a échoué. Vérifiez les logs du serveur.")

            # 3. Mettre à jour le voyage en BDD
            trip.is_published = True
            trip.published_filename = filename
            db.session.commit()

            # 4. Logger l'activité
            log_activity('trip_published', g.user.id, g.agency.id, trip.id, f"Fiche publiée : {filename}")

            return jsonify({'success': True, 'message': 'Fiche de voyage publiée avec succès !', 'trip': trip.to_dict()})

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur lors de la publication FTP du voyage {trip_id}: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500

    # NOUVEAU : Route pour créer un lien de paiement Stripe
    @app.route('/api/trips/<int:trip_id>/create-payment-link', methods=['POST'])
    @agency_required
    def api_create_payment_link(trip_id):
        """Crée un lien de paiement Stripe pour un acompte."""
        trip = Trip.query.get_or_404(trip_id)

        # Sécurité
        if trip.agency_id != g.agency.id or (g.user.role == 'seller' and trip.user_id != g.user.id):
            abort(403)

        # Vérifier que le voyage est au moins assigné
        if trip.status == 'proposed':
            return jsonify({'success': False, 'message': 'Veuillez assigner un client avant de créer un lien de paiement.'}), 400

        data = request.get_json()
        amount = data.get('amount')

        if not amount or not isinstance(amount, int) or amount <= 0:
            return jsonify({'success': False, 'message': 'Veuillez fournir un montant valide pour l\'acompte.'}), 400

        stripe_api_key = g.agency_config.get('stripe_api_key')
        if not stripe_api_key:
            return jsonify({'success': False, 'message': 'La clé API Stripe est manquante pour cette agence.'}), 400

        try:
            # MODIFIÉ : L'URL de succès pointe maintenant vers une page dédiée
            success_url = url_for('payment_success', _external=True)
            
            payment_link = create_stripe_payment_link(trip.destination, amount * 100, stripe_api_key, success_url)

            # Sauvegarder les informations dans la BDD
            trip.down_payment_amount = amount
            trip.stripe_payment_link = payment_link
            db.session.commit()

            log_activity('payment_link_created', g.user.id, g.agency.id, trip.id, f"Lien de paiement de {amount}€ créé")

            return jsonify({'success': True, 'message': 'Lien de paiement créé avec succès !', 'payment_link': payment_link})

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur lors de la création du lien de paiement Stripe pour le voyage {trip_id}: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # NOUVEAU : Route pour demander un paiement manuel
    @app.route('/api/trips/<int:trip_id>/request-manual-payment', methods=['POST'])
    @agency_required
    def api_request_manual_payment(trip_id):
        """Enregistre une demande de paiement manuel pour un acompte."""
        trip = Trip.query.get_or_404(trip_id)

        # Sécurité
        if trip.agency_id != g.agency.id or (g.user.role == 'seller' and trip.user_id != g.user.id):
            abort(403)

        if trip.status == 'proposed':
            return jsonify({'success': False, 'message': 'Veuillez assigner un client avant de demander un paiement.'}), 400

        data = request.get_json()
        amount = data.get('amount')

        if not amount or not isinstance(amount, int) or amount <= 0:
            return jsonify({'success': False, 'message': 'Veuillez fournir un montant valide.'}), 400

        try:
            trip.down_payment_amount = amount
            trip.payment_method = 'manual'
            trip.down_payment_status = 'requested'
            db.session.commit()

            # MODIFIÉ : Envoyer l'email au client
            try:
                send_manual_payment_email(
                    app_mail=mail,
                    agency_mail_config=g.agency_config.get('mail_config', {}),
                    agency_name=g.agency.name,
                    email_template=g.agency.manual_payment_email_template,
                    trip=trip,
                    client=trip.client,
                    amount=amount
                )
            except Exception as mail_error:
                # Ne pas bloquer l'utilisateur, mais logger l'erreur
                app.logger.warning(f"Erreur d'envoi d'email pour le voyage {trip.id}: {mail_error}")

            log_activity('manual_payment_requested', g.user.id, g.agency.id, trip.id, f"Acompte de {amount}€ demandé (manuel)")

            return jsonify({'success': True, 'message': 'Demande de paiement manuel enregistrée avec succès.'})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur lors de la demande de paiement manuel pour le voyage {trip.id}: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500

    # NOUVEAU : Route pour marquer un paiement manuel comme payé
    @app.route('/api/trips/<int:trip_id>/mark-as-paid', methods=['POST'])
    @agency_required
    def api_mark_as_paid(trip_id):
        """Marque l'acompte d'un paiement manuel comme payé."""
        trip = Trip.query.get_or_404(trip_id)

        # Sécurité
        if trip.agency_id != g.agency.id or (g.user.role == 'seller' and trip.user_id != g.user.id):
            abort(403)

        if trip.payment_method != 'manual':
            return jsonify({'success': False, 'message': 'Cette action est réservée aux paiements manuels.'}), 400

        try:
            trip.down_payment_status = 'paid'
            db.session.commit()

            log_activity(
                action='manual_payment_paid',
                user_id=g.user.id,
                agency_id=g.agency.id,
                trip_id=trip.id,
                details=f"Acompte de {trip.down_payment_amount}€ marqué comme payé"
            )

            return jsonify({'success': True, 'message': 'Paiement marqué comme payé avec succès.'})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur lors du marquage comme payé pour le voyage {trip.id}: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500

    # NOUVEAU : Route pour envoyer l'offre de paiement par email
    @app.route('/api/trips/<int:trip_id>/send-offer', methods=['POST'])
    @agency_required
    def api_send_offer_email(trip_id):
        """Envoie l'offre de paiement au client par email."""
        trip = Trip.query.get_or_404(trip_id)

        # Sécurité : Vérifier l'appartenance
        if trip.agency_id != g.agency.id:
            abort(403)
        if g.user.role == 'seller' and trip.user_id != g.user.id:
            abort(403)

        # Vérifier qu'un client est assigné
        if not trip.client:
            return jsonify({'success': False, 'message': 'Aucun client assigné à ce voyage.'}), 400

        data = request.get_json()
        payment_type = data.get('payment_type', 'total')
        
        # Vérifier que la clé Stripe est configurée AVANT tout traitement
        stripe_api_key = g.agency_config.get('stripe_api_key')
        if not stripe_api_key:
            return jsonify({
                'success': False,
                'message': 'La clé API Stripe n\'est pas configurée pour votre agence. Veuillez contacter l\'administrateur.'
            }), 400
        
        try:
            # Récupérer les données complètes du voyage
            full_data = json.loads(trip.full_data_json)
            api_data = full_data.get('api_data', {})
            form_data = full_data.get('form_data', {})
            
            # URL de l'offre publique (si publiée)
            if trip.is_published and trip.published_filename:
                public_offer_url = f"{g.agency.website_url or ''}/offres/{trip.published_filename}"
            elif trip.client_published_filename:
                public_offer_url = f"{g.agency.website_url or ''}/clients/{trip.client_published_filename}"
            else:
                public_offer_url = "#"
            
            # Photo d'en-tête
            header_photo = api_data.get('photos', [''])[0] if api_data.get('photos') else ''
            
            # Logique selon le type de paiement
            if payment_type == 'down_payment':
                down_payment_amount = int(data.get('down_payment_amount', 0))
                balance_due_date_str = data.get('balance_due_date', '')
                
                if not down_payment_amount or not balance_due_date_str:
                    return jsonify({'success': False, 'message': 'Montant acompte et date solde requis.'}), 400
                
                # Parser la date
                balance_due_date = datetime.strptime(balance_due_date_str, '%Y-%m-%d').date()
                amount_to_pay = down_payment_amount
                
                # Sauvegarder dans le trip
                trip.down_payment_amount = down_payment_amount
                trip.balance_due_date = balance_due_date
                
                template = 'agency/offer_template_down_payment.html'
            else:
                amount_to_pay = trip.price
                template = 'agency/offer_template.html'
            
            # Créer le lien de paiement Stripe
            try:
                from services.payment import create_stripe_payment_link
                success_url = url_for('payment_success', _external=True)
                
                payment_link = create_stripe_payment_link(
                    f'Voyage {trip.hotel_name} - {trip.destination}',
                    amount_to_pay * 100,
                    stripe_api_key,
                    success_url
                )
                
                trip.stripe_payment_link = payment_link
                
            except Exception as stripe_error:
                app.logger.error(f"Erreur création lien Stripe: {stripe_error}", exc_info=True)
                return jsonify({
                    'success': False,
                    'message': f'Erreur lors de la création du lien de paiement: {str(stripe_error)}'
                }), 500
            
            # Préparer les variables pour le template email
            email_context = {
                'client_first_name': trip.client.first_name,
                'hotel_name': trip.hotel_name,
                'destination': trip.destination,
                'public_offer_url': public_offer_url,
                'header_photo': header_photo,
                'stripe_payment_link': payment_link,
                'agency_name': g.agency.name,
                'agency_logo': g.agency.logo_url or '',
                'agency_contact_phone': g.agency.contact_phone or '',
                'agency_contact_address': g.agency.contact_address or '',
                'agency_contact_email': g.agency.contact_email or ''
            }
            
            # Ajouter les variables spécifiques à l'acompte si nécessaire
            if payment_type == 'down_payment':
                email_context.update({
                    'down_payment_amount': down_payment_amount,
                    'balance_amount': trip.price - down_payment_amount,
                    'balance_due_date': balance_due_date.strftime('%d/%m/%Y')
                })
            
            # Envoyer l'email
            msg = Message(
                subject=f'Votre proposition de voyage - {trip.hotel_name}',
                recipients=[trip.client.email],
                html=render_template(template, **email_context)
            )
            
            mail.send(msg)
            
            # Sauvegarder les modifications
            db.session.commit()
            
            # Log de l'activité
            log_activity(
                action='offer_sent',
                user_id=g.user.id,
                agency_id=g.agency.id,
                trip_id=trip.id,
                details=f"Offre de {amount_to_pay}€ envoyée à {trip.client.email}"
            )
            
            return jsonify({
                'success': True,
                'message': 'Offre envoyée par email avec succès !'
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur envoi offre voyage {trip_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'message': f'Erreur lors de l\'envoi: {str(e)}'
            }), 500

    # ==============================================================================
    # ROUTES SOCIAL MEDIA
    # ==============================================================================

    @app.route('/agency/trip/<int:trip_id>/social-media')
    @agency_required
    def social_media_page(trip_id):
        """Show social media generation page for a trip"""
        trip = Trip.query.filter_by(
            id=trip_id, 
            agency_id=g.user.agency_id
        ).first_or_404()
        
        # Récupérer toutes les campagnes existantes pour la liste
        campaigns = SocialMediaCampaign.query.filter_by(
            trip_id=trip_id
        ).order_by(SocialMediaCampaign.created_at.desc()).all()
        
        # Récupérer la campagne spécifique à charger, si un ID est fourni dans l'URL
        campaign_to_load_id = request.args.get('campaign', type=int)
        campaign_to_load = None
        if campaign_to_load_id:
            campaign_to_load = SocialMediaCampaign.query.filter_by(
                id=campaign_to_load_id, agency_id=g.user.agency_id
            ).first()

        return render_template('agency/social_media.html', 
                             trip=trip, 
                             campaigns=campaigns,
                             campaign_to_load=campaign_to_load)

    @app.route('/api/generate-social-media', methods=['POST'])
    @agency_required
    def generate_social_media():
        """API endpoint to generate social media campaign"""
        data = request.get_json()
        trip_id = data.get('trip_id')
        platform = data.get('platform', 'instagram')  # instagram, facebook, multi
        
        # Get trip
        trip = Trip.query.filter_by(
            id=trip_id,
            agency_id=g.user.agency_id
        ).first_or_404()
        
        # Get agency
        agency = Agency.query.get(g.user.agency_id)
        
        try:
            # Generate campaign
            bannerbear_config = {
                'api_key': app.config.get('BANNERBEAR_API_KEY'),
                'hero_template_id': app.config.get('BANNERBEAR_HERO_TEMPLATE_ID'),
                'service_template_id': app.config.get('BANNERBEAR_SERVICE_TEMPLATE_ID')
            }
            if not bannerbear_config['api_key'] or not bannerbear_config['hero_template_id'] or not bannerbear_config['service_template_id']:
                return jsonify({'success': False, 'error': 'La configuration Bannerbear est incomplète sur le serveur.'}), 500
            
            generator = SocialMediaGenerator(agency, trip, g.agency_config.get('google_api_key'), bannerbear_config)
            
            # Check if it's a day trip - different generation flow
            if trip.is_day_trip:
                # Day trips require a description from the user
                description = data.get('description', '')
                if not description:
                    return jsonify({
                        'success': False,
                        'error': 'Une description de l\'excursion est requise'
                    }), 400
                
                # Get day trip template ID
                day_trip_template_id = app.config.get('BANNERBEAR_DAY_TRIP_TEMPLATE_ID')
                if not day_trip_template_id or day_trip_template_id == 'GENERIC_TEMPLATE_ID':
                    return jsonify({
                        'success': False,
                        'error': 'Le template Bannerbear pour les excursions n\'est pas encore configuré. Veuillez contacter l\'administrateur.'
                    }), 500
                
                campaign_data = generator.generate_day_trip_post(description, day_trip_template_id)
            else:
                # Regular trip (sejour) - original logic
                if platform == 'instagram':
                    campaign_data = generator.generate_instagram_carousel()
                else:
                    # Can add Facebook-specific generation later
                    campaign_data = generator.generate_instagram_carousel()
            
            # Save to database
            campaign = SocialMediaCampaign(
                trip_id=trip_id,
                agency_id=agency.id,
                campaign_name=f"{trip.destination} - {platform.title()}",
                platform=platform,
                format='carousel',
                slides_data=campaign_data['slides'],
                captions=campaign_data['captions'],
                hashtags=campaign_data['hashtags']
            )
            db.session.add(campaign)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'campaign_id': campaign.id,
                'slides': campaign_data['slides'],
                'captions': campaign_data['captions']
            })
            
        except Exception as e:
            app.logger.error(f"Error generating social media: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/social-media/<int:campaign_id>/download')
    @agency_required
    def download_campaign(campaign_id):
        """Download campaign as ZIP file"""
        campaign = SocialMediaCampaign.query.filter_by(
            id=campaign_id,
            agency_id=g.user.agency_id
        ).first_or_404()
        
        # Create ZIP file in memory
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add each slide image
            for idx, slide in enumerate(campaign.slides_data):
                slide_path = slide['path']
                if os.path.exists(slide_path):
                    arc_name = f"slide_{idx+1}_{slide['type']}.jpg"
                    zip_file.write(slide_path, arc_name)
            
            # Add captions text file
            captions_content = "=== CAPTIONS RÉSEAUX SOCIAUX ===\n\n"
            
            if 'instagram' in campaign.captions:
                captions_content += "INSTAGRAM:\n"
                captions_content += campaign.captions['instagram']
                captions_content += "\n\n"
            
            if 'facebook' in campaign.captions:
                captions_content += "FACEBOOK:\n"
                captions_content += campaign.captions['facebook']
                captions_content += "\n\n"
            
            if campaign.hashtags:
                captions_content += "HASHTAGS:\n"
                captions_content += campaign.hashtags
            
            zip_file.writestr('captions.txt', captions_content.encode('utf-8'))
        
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'campaign_{campaign.campaign_name}.zip'
        )

    @app.route('/api/social-media/<int:campaign_id>/edit', methods=['POST'])
    @agency_required
    def edit_campaign(campaign_id):
        """Edit campaign captions"""
        campaign = SocialMediaCampaign.query.filter_by(
            id=campaign_id,
            agency_id=g.user.agency_id
        ).first_or_404()
        
        data = request.get_json()
        
        if 'captions' in data:
            campaign.captions = data['captions']
        
        if 'hashtags' in data:
            campaign.hashtags = data['hashtags']
        
        campaign.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True})

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
                # Vérifier les doublons d'email dans l'agence
                email = data.get('email', '').strip().lower()
                if email:
                    existing_client = Client.query.filter(
                        Client.agency_id == g.agency.id,
                        db.func.lower(Client.email) == email
                    ).first()
                    
                    if existing_client:
                        return jsonify({
                            'success': False,
                            'message': f'Un client avec l\'email {email} existe déjà dans votre agence.',
                            'duplicate': True,
                            'existing_client': existing_client.to_dict()
                        }), 409
                
                new_client = Client(
                    agency_id=g.agency.id,
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    email=email,
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
                app.logger.error(f"Erreur lors de la création d'un client pour l'agence {g.agency.id}: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'message': f'Erreur: {str(e)}'
                }), 500
    
    @app.route('/api/crm/clients/<int:client_id>', methods=['DELETE'])
    @agency_required
    def api_delete_client(client_id):
        """Supprime un client de l'agence"""
        
        # Seuls les admins peuvent supprimer des clients
        if g.user.role != 'agency_admin':
            return jsonify({
                'success': False,
                'message': 'Accès réservé aux administrateurs'
            }), 403
        
        client = Client.query.get_or_404(client_id)
        
        # Vérifier que le client appartient à l'agence
        if client.agency_id != g.agency.id:
            abort(403)
        
        try:
            # Vérifier s'il y a des voyages associés
            trips_count = Trip.query.filter_by(client_id=client_id).count()
            
            if trips_count > 0:
                # Détacher le client des voyages au lieu de tout supprimer
                Trip.query.filter_by(client_id=client_id).update({Trip.client_id: None})
            
            # Supprimer le client (les interactions seront supprimées en cascade)
            db.session.delete(client)
            db.session.commit()
            
            # Log de l'activité
            log_activity(
                action='client_deleted',
                user_id=g.user.id,
                agency_id=g.agency.id,
                details=f'Client supprimé: {client.first_name} {client.last_name} ({trips_count} voyage(s) détaché(s))'
            )
            
            return jsonify({
                'success': True,
                'message': f'Client supprimé avec succès. {trips_count} voyage(s) ont été détachés de ce client.'
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur lors de la suppression du client {client_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'message': f'Erreur lors de la suppression: {str(e)}'
            }), 500
    
    @app.route('/api/crm/check-duplicate-email', methods=['POST'])
    @agency_required
    def api_check_duplicate_email():
        """Vérifie si un email existe déjà dans l'agence"""
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        exclude_client_id = data.get('exclude_client_id')  # Pour exclure le client en cours de modification
        
        if not email:
            return jsonify({
                'success': True,
                'is_duplicate': False
            })
        
        try:
            query = Client.query.filter(
                Client.agency_id == g.agency.id,
                db.func.lower(Client.email) == email
            )
            
            # Exclure le client actuel si modification
            if exclude_client_id:
                query = query.filter(Client.id != exclude_client_id)
            
            existing_client = query.first()
            
            if existing_client:
                return jsonify({
                    'success': True,
                    'is_duplicate': True,
                    'client': {
                        'id': existing_client.id,
                        'name': f'{existing_client.first_name} {existing_client.last_name}',
                        'email': existing_client.email
                    }
                })
            else:
                return jsonify({
                    'success': True,
                    'is_duplicate': False
                })
                
        except Exception as e:
            app.logger.error(f"Erreur check duplicate email: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # ==============================================================================
    # ROUTES CRM - GESTION DES CLIENTS AVANCÉE
    # ==============================================================================
    
    @app.route('/agency/crm')
    @agency_required
    def crm_dashboard():
        """Dashboard CRM avec statistiques et segmentation clients"""
        from datetime import timedelta
        from services.analytics import AnalyticsService
        
        # Seuls les admins ont accès complet
        if g.user.role != 'agency_admin':
            abort(403, "Accès réservé aux administrateurs")
        
        # Récupérer tous les clients de l'agence
        clients = Client.query.filter_by(agency_id=g.agency.id).order_by(
            Client.created_at.desc()
        ).all()
        
        # Calculer les statistiques
        total_clients = len(clients)
        
        # Nouveaux clients (30 derniers jours)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        new_clients = sum(1 for c in clients if c.created_at >= thirty_days_ago)
        
        # Clients VIP
        vip_clients = sum(1 for c in clients if c.client_type == 'vip')
        
        # LTV moyen (Lifetime Value)
        total_revenue = sum(c.total_revenue or 0 for c in clients)
        average_ltv = total_revenue // total_clients if total_clients > 0 else 0
        
        # Segmentation
        segments = {
            'nouveau': sum(1 for c in clients if c.client_type == 'nouveau' or not c.client_type),
            'regulier': sum(1 for c in clients if c.client_type == 'regulier'),
            'vip': sum(1 for c in clients if c.client_type == 'vip')
        }
        
        stats = {
            'total_clients': total_clients,
            'new_clients': new_clients,
            'vip_clients': vip_clients,
            'average_ltv': average_ltv
        }
        
        return render_template('agency/crm/dashboard.html', 
                             clients=clients, 
                             stats=stats,
                             segments=segments)
    
    @app.route('/agency/crm/clients/<int:client_id>')
    @agency_required
    def client_detail(client_id):
        """Fiche détaillée d'un client avec historique"""
        from services.analytics import AnalyticsService

        client = Client.query.get_or_404(client_id)

        # Vérifier que le client appartient à l'agence
        if client.agency_id != g.agency.id:
            abort(403)

        # NOTE: La synchronisation automatique a été désactivée pour améliorer les performances
        # La synchronisation se fait désormais uniquement:
        # - Manuellement via le bouton dans les paramètres
        # - Automatiquement en arrière-plan via le scheduler (si configuré)

        # Récupérer l'historique des voyages
        trips = Trip.query.filter_by(client_id=client_id).order_by(
            Trip.created_at.desc()
        ).all()

        # Récupérer l'historique des interactions
        interactions = ClientInteraction.query.options(
            joinedload(ClientInteraction.user)
        ).filter_by(client_id=client_id).order_by(
            ClientInteraction.created_at.desc()
        ).all()

        # Obtenir les insights du client
        insights = AnalyticsService.get_client_insights(client_id)
        
        return render_template('agency/crm/client_detail.html',
                             client=client,
                             trips=trips,
                             interactions=interactions,
                             insights=insights,
                             agency=g.agency)
    
    # ==============================================================================
    # API CRM - INTERACTIONS ET NOTES
    # ==============================================================================
    
    @app.route('/api/crm/interactions', methods=['POST'])
    @agency_required
    def api_create_interaction():
        """Créer une nouvelle interaction avec un client"""
        from models import ClientInteraction
        
        data = request.get_json()
        client_id = data.get('client_id')
        interaction_type = data.get('interaction_type')
        content = data.get('content')
        
        if not all([client_id, interaction_type, content]):
            return jsonify({
                'success': False,
                'error': 'Données manquantes'
            }), 400
        
        # Vérifier que le client appartient à l'agence
        client = Client.query.get_or_404(client_id)
        if client.agency_id != g.agency.id:
            abort(403)
        
        try:
            interaction = ClientInteraction(
                client_id=client_id,
                user_id=g.user.id,
                interaction_type=interaction_type,
                content=content
            )
            
            db.session.add(interaction)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'interaction': interaction.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur création interaction: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/crm/clients/<int:client_id>/notes', methods=['PUT'])
    @agency_required
    def api_update_client_notes(client_id):
        """Mettre à jour les notes d'un client"""
        client = Client.query.get_or_404(client_id)
        
        if client.agency_id != g.agency.id:
            abort(403)
        
        data = request.get_json()
        notes = data.get('notes', '')
        
        try:
            client.notes = notes
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Notes mises à jour'
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur mise à jour notes: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # ==============================================================================
    # API CRM - EXPORT
    # ==============================================================================
    
    @app.route('/api/crm/export')
    @agency_required
    def api_export_clients():
        """Exporter la liste des clients en CSV ou Excel"""
        from services.reports import ReportsService
        
        if g.user.role != 'agency_admin':
            abort(403)
        
        format_type = request.args.get('format', 'csv')
        client_type = request.args.get('type')
        
        if client_type == 'all':
            client_type = None
        
        try:
            if format_type == 'csv':
                output = ReportsService.export_clients_to_csv(g.agency.id, client_type)
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'text/csv'
                response.headers['Content-Disposition'] = 'attachment; filename=clients.csv'
            else:  # excel
                output = ReportsService.export_clients_to_excel(g.agency.id, client_type)
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                response.headers['Content-Disposition'] = 'attachment; filename=clients.xlsx'
            
            return response
            
        except Exception as e:
            app.logger.error(f"Erreur export clients: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # ==============================================================================
    # ROUTES EMAIL SYNC - CONFIGURATION ET OAUTH
    # ==============================================================================
    
    @app.route('/agency/settings/email-sync')
    @agency_admin_required
    def email_sync_settings():
        """Page de configuration de la synchronisation email"""
        # Vérifier si un compte email est déjà connecté (OAuth OU manuel)
        is_connected = (
            g.agency.email_access_token_encrypted is not None or
            (g.agency.smtp_config_encrypted is not None and g.agency.imap_config_encrypted is not None)
        )
        
        # Récupérer les statistiques de synchronisation
        if is_connected:
            # Compter les interactions email
            from models import ClientInteraction
            email_count = ClientInteraction.query.filter_by(
                interaction_type='email'
            ).join(Client).filter(
                Client.agency_id == g.agency.id
            ).count()
            
            last_sync = g.agency.email_last_sync_at
        else:
            email_count = 0
            last_sync = None
        
        return render_template('agency/settings/email_sync.html',
                             is_connected=is_connected,
                             email_provider=g.agency.email_sync_provider or g.agency.email_provider,
                             email_count=email_count,
                             last_sync=last_sync,
                             sync_enabled=g.agency.email_sync_enabled)
    
    @app.route('/oauth/gmail/authorize')
    @agency_admin_required
    def gmail_oauth_authorize():
        """Initie le flow OAuth2 Gmail"""
        from google_auth_oauthlib.flow import Flow
        
        # Configuration OAuth
        client_config = {
            "web": {
                "client_id": app.config.get('GMAIL_CLIENT_ID'),
                "client_secret": app.config.get('GMAIL_CLIENT_SECRET'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [app.config.get('GMAIL_REDIRECT_URI')]
            }
        }
        
        # Scopes nécessaires (lecture + envoi)
        scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.labels',
            'https://www.googleapis.com/auth/gmail.send',      # Envoi d'emails
            'https://www.googleapis.com/auth/gmail.modify'     # Modifier emails (marquer comme lu, etc.)
        ]
        
        try:
            flow = Flow.from_client_config(
                client_config,
                scopes=scopes,
                redirect_uri=app.config.get('GMAIL_REDIRECT_URI')
            )
            
            # Générer l'URL d'autorisation
            authorization_url, state = flow.authorization_url(
                access_type='offline',  # Pour obtenir un refresh token
                include_granted_scopes='true',
                prompt='consent'  # Force l'affichage du consentement
            )
            
            # Stocker le state dans la session pour validation
            session['oauth_state'] = state
            session['agency_id'] = g.agency.id
            
            return redirect(authorization_url)
            
        except Exception as e:
            app.logger.error(f"Erreur OAuth authorize: {e}", exc_info=True)
            return render_template('error.html',
                                 message=f'Erreur lors de l\'authentification: {str(e)}')
    
    @app.route('/oauth/gmail/callback')
    @agency_admin_required
    def gmail_oauth_callback():
        """Traite le retour de l'authentification OAuth Gmail"""
        from google_auth_oauthlib.flow import Flow
        from utils.crypto import encrypt_api_key
        
        # Vérifier le state pour prévenir CSRF
        state = session.get('oauth_state')
        if not state or state != request.args.get('state'):
            return render_template('error.html',
                                 message='Erreur de sécurité: state invalide')
        
        # Configuration OAuth
        client_config = {
            "web": {
                "client_id": app.config.get('GMAIL_CLIENT_ID'),
                "client_secret": app.config.get('GMAIL_CLIENT_SECRET'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [app.config.get('GMAIL_REDIRECT_URI')]
            }
        }
        
        scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.labels'
        ]
        
        try:
            flow = Flow.from_client_config(
                client_config,
                scopes=scopes,
                state=state,
                redirect_uri=app.config.get('GMAIL_REDIRECT_URI')
            )
            
            # Échanger le code d'autorisation contre des tokens
            flow.fetch_token(authorization_response=request.url)
            credentials = flow.credentials
            
            # Chiffrer et stocker les tokens
            import json
            token_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            g.agency.email_access_token_encrypted = encrypt_api_key(credentials.token)
            g.agency.email_refresh_token_encrypted = encrypt_api_key(credentials.refresh_token) if credentials.refresh_token else None
            g.agency.email_provider = 'gmail'
            g.agency.email_sync_enabled = True
            g.agency.email_token_expires_at = credentials.expiry if hasattr(credentials, 'expiry') else None
            
            db.session.commit()
            
            # Log de l'activité
            log_activity(
                action='email_sync_connected',
                user_id=g.user.id,
                agency_id=g.agency.id,
                details='Compte Gmail connecté pour la synchronisation'
            )
            
            # Lancer une première synchronisation en arrière-plan (optionnel)
            # Pour le MVP, on le fait manuellement via le bouton
            
            return redirect(url_for('email_sync_settings'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur OAuth callback: {e}", exc_info=True)
            return render_template('error.html',
                                 message=f'Erreur lors de la connexion: {str(e)}')
    
    # ==============================================================================
    # API EMAIL SYNC - SYNCHRONISATION ET GESTION
    # ==============================================================================
    
    @app.route('/api/email-sync/trigger', methods=['POST'])
    @agency_admin_required
    @limiter.limit("5 per hour")  # Limite pour éviter les abus
    def trigger_email_sync():
        """Lance une synchronisation manuelle des emails"""
        from services.email_sync.email_sync_manager import EmailSyncManager
        
        if not g.agency.email_sync_enabled:
            return jsonify({
                'success': False,
                'error': 'La synchronisation email n\'est pas activée'
            }), 400
        
        try:
            # Initialiser le gestionnaire de sync
            manager = EmailSyncManager(g.agency)
            
            # Lancer la synchronisation
            stats = manager.sync_emails()
            
            # Mettre à jour la date de dernière sync
            g.agency.email_last_sync_at = datetime.utcnow()
            db.session.commit()
            
            # Log de l'activité
            log_activity(
                action='email_sync_triggered',
                user_id=g.user.id,
                agency_id=g.agency.id,
                details=f"Synchronisation: {stats['processed']} emails traités, {stats['saved']} sauvegardés"
            )
            
            return jsonify({
                'success': True,
                'message': 'Synchronisation terminée avec succès',
                'stats': stats
            })
            
        except Exception as e:
            app.logger.error(f"Erreur synchronisation emails: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Erreur lors de la synchronisation: {str(e)}'
            }), 500
    
    @app.route('/api/email-sync/status')
    @agency_admin_required
    def email_sync_status():
        """Retourne le statut de la synchronisation email"""
        from models import ClientInteraction
        
        if not g.agency.email_sync_enabled:
            return jsonify({
                'success': True,
                'connected': False,
                'provider': None
            })
        
        # Compter les emails synchronisés
        email_count = ClientInteraction.query.filter_by(
            interaction_type='email'
        ).join(Client).filter(
            Client.agency_id == g.agency.id
        ).count()
        
        # Emails des dernières 24h
        from datetime import timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_count = ClientInteraction.query.filter(
            ClientInteraction.interaction_type == 'email',
            ClientInteraction.created_at >= yesterday
        ).join(Client).filter(
            Client.agency_id == g.agency.id
        ).count()
        
        return jsonify({
            'success': True,
            'connected': True,
            'provider': g.agency.email_provider,
            'last_sync': g.agency.email_last_sync_at.isoformat() if g.agency.email_last_sync_at else None,
            'total_emails': email_count,
            'recent_emails': recent_count,
            'sync_enabled': g.agency.email_sync_enabled
        })
    
    @app.route('/api/email-sync/disconnect', methods=['POST'])
    @agency_admin_required
    def disconnect_email_sync():
        """Désactive la synchronisation email et supprime les tokens"""
        try:
            # Supprimer les tokens
            g.agency.email_access_token_encrypted = None
            g.agency.email_refresh_token_encrypted = None
            g.agency.email_sync_enabled = False
            g.agency.email_provider = None
            g.agency.email_token_expires_at = None
            
            db.session.commit()
            
            # Log de l'activité
            log_activity(
                action='email_sync_disconnected',
                user_id=g.user.id,
                agency_id=g.agency.id,
                details='Synchronisation email désactivée'
            )
            
            return jsonify({
                'success': True,
                'message': 'Synchronisation email désactivée avec succès'
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur déconnexion email sync: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/email-sync/config-manual', methods=['POST'])
    @agency_admin_required
    def api_save_manual_email_config():
        """Enregistre la configuration SMTP/IMAP manuelle"""
        from utils.crypto import encrypt_config
        
        data = request.get_json()
        smtp_config = data.get('smtp')
        imap_config = data.get('imap')
        
        if not smtp_config or not imap_config:
            return jsonify({
                'success': False,
                'error': 'Configuration SMTP et IMAP requises'
            }), 400
        
        try:
            # Chiffrer et sauvegarder
            g.agency.smtp_config_encrypted = encrypt_config(smtp_config)
            g.agency.imap_config_encrypted = encrypt_config(imap_config)
            g.agency.email_config_type = 'manual'
            g.agency.email_sync_enabled = True
            g.agency.email_sync_provider = 'manual'
            g.agency.email_sync_email = smtp_config.get('from_email')
            
            db.session.commit()
            
            # Log de l'activité
            log_activity(
                action='email_config_manual',
                user_id=g.user.id,
                agency_id=g.agency.id,
                details='Configuration email manuelle SMTP/IMAP activée'
            )
            
            return jsonify({
                'success': True,
                'message': 'Configuration enregistrée avec succès'
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur save manual config: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/email-sync/test-smtp', methods=['POST'])
    @agency_admin_required
    def api_test_smtp_connection():
        """Teste la connexion SMTP"""
        import smtplib
        
        data = request.get_json()
        smtp_config = data.get('smtp')
        
        if not smtp_config:
            return jsonify({
                'success': False,
                'error': 'Configuration SMTP requise'
            }), 400
        
        server = None
        try:
            # Tenter une connexion
            use_ssl = smtp_config.get('use_ssl', True)
            host = smtp_config['host']
            port = int(smtp_config['port'])
            username = smtp_config['username']
            password = smtp_config['password']
            
            if use_ssl:
                # SMTP_SSL se connecte automatiquement dans __init__
                server = smtplib.SMTP_SSL(host, port, timeout=10)
            else:
                # SMTP standard nécessite un appel explicite à connect()
                server = smtplib.SMTP(timeout=10)
                server.connect(host, port)
                if smtp_config.get('use_tls', False):
                    server.starttls()
            
            # Tester l'authentification
            server.login(username, password)
            server.quit()
            
            return jsonify({
                'success': True,
                'message': 'Connexion SMTP réussie'
            })
            
        except smtplib.SMTPAuthenticationError as e:
            if server:
                try:
                    server.quit()
                except:
                    pass
            return jsonify({
                'success': False,
                'error': 'Erreur d\'authentification - Vérifiez le nom d\'utilisateur et le mot de passe'
            }), 400
        except smtplib.SMTPException as e:
            if server:
                try:
                    server.quit()
                except:
                    pass
            return jsonify({
                'success': False,
                'error': f'Erreur SMTP: {str(e)}'
            }), 400
        except Exception as e:
            if server:
                try:
                    server.quit()
                except:
                    pass
            return jsonify({
                'success': False,
                'error': f'Erreur de connexion: {str(e)}'
            }), 400

    # ==============================================================================
    # ROUTES RAPPORTS & ANALYTICS
    # ==============================================================================
    
    @app.route('/agency/reports')
    @agency_required
    def reports_dashboard():
        """Dashboard des rapports de ventes"""
        from datetime import timedelta
        from models import SalesReport
        
        if g.user.role != 'agency_admin':
            abort(403)
        
        # Récupérer les rapports récents (20 derniers)
        reports = SalesReport.query.options(
            joinedload(SalesReport.agency),
            joinedload(SalesReport.user)
        ).filter_by(agency_id=g.agency.id).order_by(
            SalesReport.generated_at.desc()
        ).limit(20).all()
        
        # Statistiques pour le dashboard
        first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Rapports ce mois
        reports_this_month = SalesReport.query.filter(
            SalesReport.agency_id == g.agency.id,
            SalesReport.generated_at >= first_of_month
        ).count()
        
        # Total rapports
        total_reports = SalesReport.query.filter_by(agency_id=g.agency.id).count()
        
        # CA et ventes du mois
        sold_trips_this_month = Trip.query.filter(
            Trip.agency_id == g.agency.id,
            Trip.status == 'sold',
            Trip.sold_at >= first_of_month
        ).all()
        
        revenue_this_month = sum(trip.price for trip in sold_trips_this_month)
        sales_this_month = len(sold_trips_this_month)
        
        stats = {
            'this_month': reports_this_month,
            'total': total_reports,
            'revenue_this_month': revenue_this_month,
            'sales_this_month': sales_this_month
        }
        
        # Liste des vendeurs pour le formulaire
        sellers = User.query.filter_by(
            agency_id=g.agency.id,
            is_active=True
        ).filter(User.role.in_(['agency_admin', 'seller'])).all()
        
        return render_template('agency/reports/dashboard.html',
                             reports=reports,
                             stats=stats,
                             sellers=sellers)
    
    @app.route('/agency/reports/<int:report_id>')
    @agency_required
    def view_report(report_id):
        """Visualisation d'un rapport spécifique"""
        from models import SalesReport
        
        if g.user.role != 'agency_admin':
            abort(403)
        
        report = SalesReport.query.options(
            joinedload(SalesReport.agency),
            joinedload(SalesReport.user)
        ).get_or_404(report_id)
        
        # Vérifier que le rapport appartient à l'agence
        if report.agency_id != g.agency.id:
            abort(403)
        
        return render_template('agency/reports/view.html', report=report)
    
    @app.route('/agency/reports/compare')
    @agency_required
    def compare_reports():
        """Page de comparaison de périodes"""
        if g.user.role != 'agency_admin':
            abort(403)
        
        return render_template('agency/reports/compare.html')
    
    # ==============================================================================
    # API RAPPORTS - GÉNÉRATION ET EXPORT
    # ==============================================================================
    
    @app.route('/api/reports/generate', methods=['POST'])
    @agency_required
    def api_generate_report():
        """Génère un nouveau rapport de ventes"""
        from services.reports import ReportsService
        from datetime import datetime as dt
        
        if g.user.role != 'agency_admin':
            return jsonify({'success': False, 'error': 'Accès réservé aux administrateurs'}), 403
        
        data = request.get_json()
        period_type = data.get('period_type')
        user_id = data.get('user_id')
        
        try:
            # Convertir user_id en None si vide
            if user_id == '' or user_id is None:
                user_id = None
            else:
                user_id = int(user_id)
            
            # Gérer les dates personnalisées
            custom_start = None
            custom_end = None
            
            if period_type == 'custom':
                custom_start = dt.strptime(data.get('custom_start'), '%Y-%m-%d').date()
                custom_end = dt.strptime(data.get('custom_end'), '%Y-%m-%d').date()
            
            # Générer le rapport
            report = ReportsService.generate_period_report(
                agency_id=g.agency.id,
                period_type=period_type,
                custom_start=custom_start,
                custom_end=custom_end,
                user_id=user_id
            )
            
            return jsonify({
                'success': True,
                'report_id': report.id,
                'message': 'Rapport généré avec succès'
            })
            
        except Exception as e:
            app.logger.error(f"Erreur génération rapport: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/reports/<int:report_id>/export')
    @agency_required
    def api_export_report(report_id):
        """Exporte un rapport en Excel ou PDF"""
        from services.reports import ReportsService
        from models import SalesReport
        
        if g.user.role != 'agency_admin':
            abort(403)
        
        report = SalesReport.query.get_or_404(report_id)
        
        # Vérifier que le rapport appartient à l'agence
        if report.agency_id != g.agency.id:
            abort(403)
        
        format_type = request.args.get('format', 'excel')
        
        try:
            if format_type == 'excel':
                output = ReportsService.export_report_to_excel(report)
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                response.headers['Content-Disposition'] = f'attachment; filename=rapport_{report.report_type}_{report.period_start.strftime("%Y%m%d")}.xlsx'
            else:  # PDF
                output = ReportsService.export_report_to_pdf(report)
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = f'inline; filename=rapport_{report.report_type}_{report.period_start.strftime("%Y%m%d")}.pdf'
            
            return response
            
        except Exception as e:
            app.logger.error(f"Erreur export rapport: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/reports/compare', methods=['POST'])
    @agency_required
    def api_compare_periods():
        """Compare deux périodes de ventes"""
        from services.reports import ReportsService
        from datetime import datetime as dt
        
        if g.user.role != 'agency_admin':
            return jsonify({'success': False, 'error': 'Accès réservé aux administrateurs'}), 403
        
        data = request.get_json()
        
        try:
            period1_start = dt.strptime(data.get('period1_start'), '%Y-%m-%d').date()
            period1_end = dt.strptime(data.get('period1_end'), '%Y-%m-%d').date()
            period2_start = dt.strptime(data.get('period2_start'), '%Y-%m-%d').date()
            period2_end = dt.strptime(data.get('period2_end'), '%Y-%m-%d').date()
            
            comparison = ReportsService.get_comparison_report(
                agency_id=g.agency.id,
                period1_start=period1_start,
                period1_end=period1_end,
                period2_start=period2_start,
                period2_end=period2_end
            )
            
            return jsonify({
                'success': True,
                'comparison': comparison
            })
            
        except Exception as e:
            app.logger.error(f"Erreur comparaison périodes: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # ==============================================================================
    # ROUTES ANALYTICS - STATISTIQUES AVANCÉES (PHASE 4)
    # ==============================================================================
    
    @app.route('/agency/analytics')
    @agency_required
    def analytics_dashboard():
        """Dashboard des statistiques avancées avec graphiques"""
        if g.user.role != 'agency_admin':
            abort(403, "Accès réservé aux administrateurs")
        
        return render_template('agency/analytics/dashboard.html')
    
    # ==============================================================================
    # API ANALYTICS - DONNÉES ET STATISTIQUES
    # ==============================================================================
    
    @app.route('/api/analytics/dashboard')
    @agency_required
    def api_analytics_dashboard():
        """API pour récupérer toutes les données analytics du dashboard"""
        from services.analytics import AnalyticsService
        from datetime import datetime as dt, timedelta
        
        if g.user.role != 'agency_admin':
            return jsonify({'success': False, 'error': 'Accès réservé aux administrateurs'}), 403
        
        try:
            period_days = request.args.get('period_days', 30, type=int)
            
            # Calculer les KPIs
            metrics = AnalyticsService.get_agency_dashboard_metrics(g.agency.id, period_days)
            
            # Calculer les variations (comparaison avec période précédente)
            previous_metrics = AnalyticsService.get_agency_dashboard_metrics(
                g.agency.id, 
                period_days
            )
            
            # Tendance des ventes mensuelles
            months_to_show = 12 if period_days >= 180 else 6
            sales_trend = AnalyticsService.get_monthly_trends(g.agency.id, months_to_show)
            
            # Type de voyages (séjours vs excursions)
            all_trips = Trip.query.filter_by(
                agency_id=g.agency.id,
                status='sold'
            ).all()
            
            sejours = sum(1 for t in all_trips if not t.is_day_trip)
            excursions = sum(1 for t in all_trips if t.is_day_trip)
            
            # Top destinations
            destinations = AnalyticsService.get_destinations_analytics(g.agency.id, period_days)[:10]
            
            # Top vendeurs
            sellers = AnalyticsService.get_team_leaderboard(g.agency.id, period_days)[:10]
            
            # Taux de conversion mensuel (6 derniers mois)
            conversion_months = []
            conversion_rates = []
            
            for i in range(5, -1, -1):
                month_start = (dt.now().replace(day=1) - timedelta(days=i*30)).replace(day=1)
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                
                month_trips = Trip.query.filter(
                    Trip.agency_id == g.agency.id,
                    Trip.created_at >= month_start,
                    Trip.created_at <= month_end
                ).all()
                
                month_sold = sum(1 for t in month_trips if t.status == 'sold')
                month_rate = (month_sold / len(month_trips) * 100) if month_trips else 0
                
                conversion_months.append(month_start.strftime('%Y-%m'))
                conversion_rates.append(round(month_rate, 2))
            
            # Prévisions (basées sur la moyenne des 6 derniers mois)
            forecast_months = sales_trend['months'][-6:] if len(sales_trend['months']) >= 6 else sales_trend['months']
            forecast_revenue = sales_trend['revenue'][-6:] if len(sales_trend['revenue']) >= 6 else sales_trend['revenue']
            
            # Calculer moyenne et tendance
            avg_revenue = sum(forecast_revenue) / len(forecast_revenue) if forecast_revenue else 0
            
            # Projeter 3 mois dans le futur
            future_months = []
            future_revenue = []
            last_month = dt.strptime(forecast_months[-1], '%Y-%m') if forecast_months else dt.now()
            
            for i in range(1, 4):
                next_month = (last_month + timedelta(days=32*i)).replace(day=1)
                future_months.append(next_month.strftime('%Y-%m'))
                # Simple projection basée sur la moyenne
                future_revenue.append(int(avg_revenue * 1.05))  # 5% de croissance optimiste
            
            # Préparer la réponse
            response_data = {
                'success': True,
                'kpis': {
                    'total_revenue': metrics['total_revenue'],
                    'sold_trips': metrics['sold_trips'],
                    'conversion_rate': metrics['conversion_rate'],
                    'average_sale': metrics['average_sale'],
                    'revenue_change': 0,  # À calculer si besoin
                    'sales_change': 0,
                    'conversion_change': 0,
                    'average_change': 0
                },
                'sales_trend': sales_trend,
                'trip_types': {
                    'sejours': sejours,
                    'excursions': excursions
                },
                'destinations': destinations,
                'sellers': sellers,
                'conversion_trend': {
                    'months': conversion_months,
                    'rates': conversion_rates
                },
                'forecast': {
                    'months': forecast_months + future_months,
                    'actual': forecast_revenue + [None] * 3,
                    'forecast': [None] * len(forecast_revenue) + future_revenue
                }
            }
            
            return jsonify(response_data)
            
        except Exception as e:
            app.logger.error(f"Erreur API analytics dashboard: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # ==============================================================================
    # ROUTES ÉQUIPE (VENDEURS) - PHASE 5
    # ==============================================================================
    
    @app.route('/agency/sellers')
    @agency_required
    def sellers_dashboard():
        """Dashboard de gestion de l'équipe commerciale"""
        from services.analytics import AnalyticsService
        from datetime import timedelta
        
        if g.user.role != 'agency_admin':
            abort(403, "Accès réservé aux administrateurs")
        
        # Récupérer tous les vendeurs actifs de l'agence
        sellers = User.query.filter_by(
            agency_id=g.agency.id,
            is_active=True
        ).filter(User.role.in_(['agency_admin', 'seller'])).all()
        
        # Calculer les statistiques de l'équipe pour ce mois
        first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        total_revenue = 0
        total_sales = 0
        total_proposed = 0
        
        # Calculer les stats actuelles de chaque vendeur
        for seller in sellers:
            seller_trips = Trip.query.filter(
                Trip.agency_id == g.agency.id,
                Trip.user_id == seller.id,
                Trip.created_at >= first_of_month
            ).all()
            
            seller.current_revenue = sum(t.price for t in seller_trips if t.status == 'sold')
            seller.sales_count = sum(1 for t in seller_trips if t.status == 'sold')
            
            total_revenue += seller.current_revenue
            total_sales += seller.sales_count
            total_proposed += len(seller_trips)
        
        # Calculer le taux de conversion global
        conversion_rate = (total_sales / total_proposed * 100) if total_proposed > 0 else 0
        
        # Récupérer le leaderboard
        leaderboard = AnalyticsService.get_team_leaderboard(g.agency.id, 30)
        
        stats = {
            'total_sellers': len(sellers),
            'total_revenue': total_revenue,
            'total_sales': total_sales,
            'conversion_rate': round(conversion_rate, 2)
        }
        
        return render_template('agency/sellers/dashboard.html',
                             sellers=sellers,
                             leaderboard=leaderboard,
                             stats=stats)
    
    @app.route('/agency/sellers/<int:seller_id>')
    @agency_required
    def seller_detail(seller_id):
        """Page de détail d'un vendeur avec ses performances"""
        from services.analytics import AnalyticsService
        
        if g.user.role != 'agency_admin':
            abort(403, "Accès réservé aux administrateurs")
        
        seller = User.query.get_or_404(seller_id)
        
        # Vérifier que le vendeur appartient à l'agence
        if seller.agency_id != g.agency.id:
            abort(403)
        
        # Récupérer la performance du vendeur
        performance = AnalyticsService.get_seller_performance(seller_id, 30)
        
        # Récupérer les dernières ventes
        recent_sales = Trip.query.options(
            joinedload(Trip.client)
        ).filter_by(
            user_id=seller_id,
            status='sold'
        ).order_by(Trip.sold_at.desc()).limit(10).all()
        
        return render_template('agency/sellers/detail.html',
                             seller=seller,
                             performance=performance,
                             recent_sales=recent_sales)
    
    # ==============================================================================
    # API ÉQUIPE (VENDEURS) - GESTION DES OBJECTIFS
    # ==============================================================================
    
    @app.route('/api/sellers/<int:seller_id>/objectives', methods=['PUT'])
    @agency_required
    def api_update_seller_objectives(seller_id):
        """Mettre à jour les objectifs et taux de commission d'un vendeur"""
        if g.user.role != 'agency_admin':
            return jsonify({'success': False, 'error': 'Accès réservé aux administrateurs'}), 403
        
        seller = User.query.get_or_404(seller_id)
        
        # Vérifier que le vendeur appartient à l'agence
        if seller.agency_id != g.agency.id:
            abort(403)
        
        data = request.get_json()
        sales_target = data.get('sales_target')
        commission_rate = data.get('commission_rate')
        
        try:
            if sales_target is not None:
                seller.sales_target = int(sales_target)
            
            if commission_rate is not None:
                commission_rate = int(commission_rate)
                if commission_rate < 0 or commission_rate > 100:
                    return jsonify({
                        'success': False,
                        'error': 'Le taux de commission doit être entre 0 et 100'
                    }), 400
                seller.commission_rate = commission_rate
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Objectifs mis à jour avec succès',
                'seller': seller.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur mise à jour objectifs vendeur {seller_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # ==============================================================================
    # ROUTES INSPIRATION - RECHERCHE INTELLIGENTE DE VOYAGES
    # ==============================================================================
    
    @app.route('/agency/inspiration')
    @agency_required
    def inspiration():
        """Page d'inspiration de voyages avec recherche intelligente"""
        return render_template('agency/inspiration.html')
    
    @app.route('/api/search-airport', methods=['POST'])
    @agency_required
    def api_search_airport():
        """
        Recherche d'aéroports via Google Flights 2 API
        Pour l'autocomplétion des champs destination/départ
        
        POST Body:
            { "query": "paris" }
        
        Response:
            {
                "success": true,
                "airports": [
                    {
                        "code": "CDG",
                        "name": "Paris Charles de Gaulle",
                        "city": "Paris",
                        "country": "France"
                    },
                    ...
                ]
            }
        """
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query or len(query) < 2:
            return jsonify({
                'success': False,
                'error': 'Veuillez saisir au moins 2 caractères'
            }), 400
        
        rapidapi_key = app.config.get('RAPIDAPI_KEY')
        
        if not rapidapi_key:
            return jsonify({
                'success': False,
                'error': 'Service non configuré'
            }), 500
        
        try:
            url = "https://google-flights2.p.rapidapi.com/api/v1/searchAirport"
            
            headers = {
                "x-rapidapi-key": rapidapi_key,
                "x-rapidapi-host": "google-flights2.p.rapidapi.com"
            }
            
            params = {
                "query": query,
                "language_code": "fr-FR",
                "country_code": "BE"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=5)
            response.raise_for_status()
            result = response.json()
            
            # Parser la réponse
            airports = []
            if result.get('data') and isinstance(result['data'], list):
                for airport in result['data'][:10]:  # Limiter à 10 résultats
                    airports.append({
                        'code': airport.get('code', ''),
                        'name': airport.get('name', ''),
                        'city': airport.get('city', ''),
                        'country': airport.get('country', '')
                    })
            
            return jsonify({
                'success': True,
                'airports': airports
            })
            
        except requests.Timeout:
            return jsonify({
                'success': False,
                'error': 'Timeout - API ne répond pas'
            }), 504
        except Exception as e:
            app.logger.error(f"Erreur search airport: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Erreur: {str(e)}'
            }), 500
    
    @app.route('/api/inspire', methods=['POST'])
    @agency_required
    @limiter.limit("30 per hour", key_func=lambda: session.get('user_id'))
    def api_inspire():
        """
        API pour rechercher des options de voyage via IA
        
        POST Body:
            { "query": "4 jours à Rome, hotel avec petit déjeuner, budget 400€ par personne" }
        
        Response:
            {
                "success": true,
                "criteria": {
                    "destination": "Rome",
                    "budget_pp": 400,
                    "date_debut": "2025-10-03",
                    "date_fin": "2025-10-09",
                    ...
                },
                "options": [
                    {
                        "destination": "Rome",
                        "total_price": 360,
                        "hotel": {...},
                        "flight": {...}
                    },
                    ...
                ],
                "count": 3
            }
        """
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Veuillez décrire votre voyage idéal'
            }), 400
        
        # Récupérer la clé Gemini
        gemini_api_key = get_gemini_api_key()
        
        if not gemini_api_key:
            return jsonify({
                'success': False,
                'error': 'Service d\'inspiration non configuré. Contactez votre administrateur.'
            }), 500
        
        try:
            from services.travel_inspector import search_travel_inspiration
            
            # Récupérer la clé RapidAPI
            rapidapi_key = app.config.get('RAPIDAPI_KEY')
            
            # Rechercher des options de voyage
            result = search_travel_inspiration(query, gemini_api_key, rapidapi_key)
            
            if not result.get('success'):
                return jsonify(result), 400
            
            # Log de l'activité
            log_activity(
                action='inspiration_search',
                user_id=g.user.id,
                agency_id=g.agency.id,
                details=f"Recherche: {query[:100]}"
            )
            
            return jsonify(result)
            
        except Exception as e:
            app.logger.error(f"Erreur API inspire: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Erreur lors de la recherche: {str(e)}'
            }), 500
    
    # ==============================================================================
    # API AGENCE - UTILITAIRES
    # ==============================================================================
    
    @app.route('/api/ai-generate-program', methods=['POST'])
    @agency_required
    @limiter.limit("60 per hour", key_func=lambda: session.get('user_id'))
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
            app.logger.error(f"Erreur génération programme: {e}", exc_info=True)
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
    
    # NOUVEAU : Page de confirmation de paiement pour le client
    @app.route('/payment-success')
    def payment_success():
        """Page de confirmation affichée au client après un paiement réussi."""
        return render_template('payment_success.html')
    
    # NOUVEAU : Téléchargement du fichier upload.php pour l'agence
    @app.route('/agency/download-upload-php')
    @agency_required
    def download_upload_php():
        """Génère et télécharge le fichier upload.php personnalisé pour l'agence."""
        from services.upload_php_generator import generate_upload_php
        import secrets
        
        # Récupérer les informations de l'agence
        agency = g.agency
        
        # Générer une clé API si elle n'existe pas dans la config FTP
        ftp_config = g.agency_config.get('ftp_config', {})
        api_key = ftp_config.get('password', '') or secrets.token_urlsafe(32)
        
        # Déterminer le domaine
        domain = agency.website_url
        if domain:
            # Nettoyer l'URL pour extraire juste le domaine
            domain = domain.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
        else:
            domain = f"{agency.subdomain}.odyssee.com"
        
        # Chemin de base (à personnaliser selon l'hébergeur)
        base_path = '/home/uXXXXXXXXX/domains/VOTRE-DOMAINE/public_html/'
        
        # Générer le contenu PHP
        php_content = generate_upload_php(domain, api_key, base_path)
        
        # Créer la réponse de téléchargement
        response = make_response(php_content)
        response.headers['Content-Type'] = 'application/x-php'
        response.headers['Content-Disposition'] = f'attachment; filename=upload.php'
        
        return response

    # ==============================================================================
    # API EMAIL - ENVOI ET RÉPONSE (PHASE EMAIL REPLY)
    # ==============================================================================
    
    @app.route('/api/email/send', methods=['POST'])
    @agency_required
    @limiter.limit("20 per hour")
    def api_send_email():
        """
        Envoie un nouvel email via le compte connecté
        
        POST Body:
            {
                "to": "client@example.com",
                "subject": "Sujet de l'email",
                "body": "Corps de l'email en texte brut",
                "html_body": "<p>Corps en HTML</p>" (optionnel),
                "cc": "copie@example.com" (optionnel),
                "bcc": "copie_cachee@example.com" (optionnel)
            }
        
        Response:
            {
                "success": true,
                "message": "Email envoyé avec succès",
                "message_id": "...",
                "sent_at": "2025-10-30T16:30:00"
            }
        """
        if not g.agency.email_sync_enabled:
            return jsonify({
                'success': False,
                'error': 'La synchronisation email n\'est pas activée pour votre agence'
            }), 400
        
        data = request.get_json()
        to = data.get('to', '').strip()
        subject = data.get('subject', '').strip()
        body = data.get('body', '').strip()
        html_body = data.get('html_body')
        cc = data.get('cc')
        bcc = data.get('bcc')
        
        # Validation
        if not to or not subject or not body:
            return jsonify({
                'success': False,
                'error': 'Les champs to, subject et body sont requis'
            }), 400
        
        try:
            from services.email_sync.email_sender import EmailSender, EmailSendError
            
            # Initialiser le service d'envoi
            sender = EmailSender(g.agency.id)
            
            # Envoyer l'email
            result = sender.send_email(
                to=to,
                subject=subject,
                body=body,
                html_body=html_body,
                cc=cc,
                bcc=bcc
            )
            
            # Enregistrer l'email dans les interactions
            client_id = data.get('client_id')
            if client_id:
                client = Client.query.get(client_id)
                if client and client.agency_id == g.agency.id:
                    interaction = ClientInteraction(
                        client_id=client_id,
                        user_id=g.user.id,
                        interaction_type='email',
                        content=body,
                        email_subject=subject,
                        email_from=g.agency.email_sync_email or 'agence',
                        email_to=to,
                        is_outbound=True
                    )
                    db.session.add(interaction)
                    db.session.commit()
            
            # Log de l'activité
            log_activity(
                action='email_sent',
                user_id=g.user.id,
                agency_id=g.agency.id,
                details=f"Email envoyé à {to}: {subject}"
            )
            
            return jsonify({
                'success': True,
                'message': 'Email envoyé avec succès',
                'message_id': result['message_id'],
                'sent_at': result['sent_at'].isoformat() if result.get('sent_at') else None
            })
            
        except EmailSendError as e:
            app.logger.error(f"Erreur envoi email: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        except Exception as e:
            app.logger.error(f"Erreur inattendue envoi email: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Erreur lors de l\'envoi: {str(e)}'
            }), 500
    
    @app.route('/api/email/reply', methods=['POST'])
    @agency_required
    @limiter.limit("20 per hour")
    def api_reply_email():
        """
        Répond à un email existant depuis la fiche client
        
        POST Body:
            {
                "interaction_id": 123,
                "body": "Corps de la réponse",
                "html_body": "<p>Réponse en HTML</p>" (optionnel),
                "cc": "copie@example.com" (optionnel),
                "bcc": "copie_cachee@example.com" (optionnel)
            }
        
        Response:
            {
                "success": true,
                "message": "Réponse envoyée avec succès",
                "message_id": "...",
                "sent_at": "2025-10-30T16:30:00"
            }
        """
        if not g.agency.email_sync_enabled:
            return jsonify({
                'success': False,
                'error': 'La synchronisation email n\'est pas activée pour votre agence'
            }), 400
        
        data = request.get_json()
        interaction_id = data.get('interaction_id')
        body = data.get('body', '').strip()
        html_body = data.get('html_body')
        cc = data.get('cc')
        bcc = data.get('bcc')
        
        # Validation
        if not interaction_id or not body:
            return jsonify({
                'success': False,
                'error': 'Les champs interaction_id et body sont requis'
            }), 400
        
        try:
            from services.email_sync.email_sender import EmailSender, EmailSendError
            
            # Initialiser le service d'envoi
            sender = EmailSender(g.agency.id)
            
            # Envoyer la réponse
            result = sender.reply_to_email(
                interaction_id=interaction_id,
                body=body,
                html_body=html_body,
                cc=cc,
                bcc=bcc
            )
            
            # Log de l'activité
            log_activity(
                action='email_reply_sent',
                user_id=g.user.id,
                agency_id=g.agency.id,
                details=f"Réponse envoyée pour l'interaction #{interaction_id}"
            )
            
            return jsonify({
                'success': True,
                'message': 'Réponse envoyée avec succès',
                'message_id': result['message_id'],
                'sent_at': result['sent_at'].isoformat() if result.get('sent_at') else None
            })
            
        except EmailSendError as e:
            app.logger.error(f"Erreur réponse email: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        except Exception as e:
            app.logger.error(f"Erreur inattendue réponse email: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Erreur lors de l\'envoi de la réponse: {str(e)}'
            }), 500

    # ==============================================================================
    # ÉVÉNEMENTS SOCKETIO - NOTIFICATIONS TEMPS RÉEL
    # ==============================================================================
    
    @socketio.on('connect')
    def handle_connect():
        """Quand un utilisateur se connecte au système de notifications"""
        if 'user_id' not in session:
            return False  # Refuser connexion non authentifiée
        
        user_id = session['user_id']
        agency_id = session.get('agency_id')
        
        if agency_id:
            # Rejoindre la room de son agence
            room = f'agency_{agency_id}'
            join_room(room)
            
            # Envoyer le compteur d'emails non lus
            from services.notification_service import NotificationService
            unread_count = NotificationService.get_unread_count(agency_id, user_id)
            
            emit('unread_count', {'count': unread_count})
            
            # Envoyer les emails récents non lus
            recent_emails = NotificationService.get_recent_unread_emails(agency_id, limit=5)
            emit('recent_emails', {'emails': recent_emails})
            
            app.logger.info(f"User {user_id} connected to agency room {room}")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Quand un utilisateur se déconnecte"""
        if 'agency_id' in session:
            room = f'agency_{session["agency_id"]}'
            leave_room(room)
            app.logger.info(f"User disconnected from room {room}")
    
    @socketio.on('mark_read')
    def handle_mark_read(data):
        """Marque un email comme lu"""
        if 'user_id' not in session:
            return
        
        interaction_id = data.get('interaction_id')
        user_id = session['user_id']
        
        from services.notification_service import NotificationService
        success = NotificationService.mark_as_read(interaction_id, user_id)
        
        if success:
            emit('marked_read', {'interaction_id': interaction_id})
    
    @socketio.on('mark_all_read')
    def handle_mark_all_read():
        """Marque tous les emails comme lus"""
        if 'user_id' not in session or 'agency_id' not in session:
            return
        
        user_id = session['user_id']
        agency_id = session['agency_id']
        
        from services.notification_service import NotificationService
        count = NotificationService.mark_all_as_read(agency_id, user_id)
        
        if count > 0:
            emit('all_marked_read', {'count': count})
            emit('unread_count', {'count': 0})
    
    # ==============================================================================
    # ROUTES EMAIL ANALYTICS ET RECHERCHE (ÉTAPE 3)
    # ==============================================================================
    
    @app.route('/agency/email-analytics')
    @agency_required
    def email_analytics():
        """Dashboard des analytics emails"""
        from services.email_sync.analytics import EmailAnalyticsService
        from datetime import datetime, timedelta
        
        if g.user.role != 'agency_admin':
            abort(403, "Accès réservé aux administrateurs")
        
        # Récupérer les paramètres de période
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Dates par défaut (30 derniers jours)
        if not end_date_str:
            end_date = datetime.now().date()
        else:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        if not start_date_str:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        
        try:
            # Récupérer toutes les analytics
            analytics = EmailAnalyticsService.get_comprehensive_analytics(
                g.agency.id,
                start_date,
                end_date
            )
            
            return render_template('agency/email_analytics.html',
                                 analytics=analytics,
                                 start_date=start_date.strftime('%Y-%m-%d'),
                                 end_date=end_date.strftime('%Y-%m-%d'))
        
        except Exception as e:
            app.logger.error(f"Erreur email analytics: {e}", exc_info=True)
            return render_template('error.html',
                                 message=f'Erreur lors du chargement des analytics: {str(e)}')
    
    @app.route('/agency/email-search')
    @agency_required
    def email_search():
        """Page de recherche d'emails"""
        from services.email_sync.search import EmailSearchService
        
        # Récupérer les paramètres de recherche
        query = request.args.get('query', '').strip()
        sender = request.args.get('sender', '').strip()
        recipient = request.args.get('recipient', '').strip()
        direction = request.args.get('direction', '').strip()
        start_date_str = request.args.get('start_date', '').strip()
        end_date_str = request.args.get('end_date', '').strip()
        category = request.args.get('category', '').strip()
        sentiment = request.args.get('sentiment', '').strip()
        thread_id = request.args.get('thread_id', '').strip()
        page = request.args.get('page', 1, type=int)
        
        results = []
        total_pages = 0
        
        # Si au moins un critère de recherche est fourni
        if any([query, sender, recipient, start_date_str, thread_id]):
            try:
                # Convertir les dates
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
                
                # Effectuer la recherche
                search_results = EmailSearchService.search_emails(
                    agency_id=g.agency.id,
                    query=query if query else None,
                    sender=sender if sender else None,
                    recipient=recipient if recipient else None,
                    start_date=start_date,
                    end_date=end_date,
                    direction='received' if direction == 'received' else ('sent' if direction == 'sent' else None),
                    category=category if category else None,
                    sentiment=sentiment if sentiment else None,
                    thread_id=thread_id if thread_id else None,
                    page=page,
                    per_page=20
                )
                
                results = search_results['results']
                total_pages = search_results['total_pages']
                
            except Exception as e:
                app.logger.error(f"Erreur recherche email: {e}", exc_info=True)
        
        return render_template('agency/email_search.html',
                             results=results,
                             total_pages=total_pages,
                             page=page,
                             query=query,
                             sender=sender,
                             recipient=recipient,
                             direction=direction,
                             start_date=start_date_str,
                             end_date=end_date_str,
                             category=category,
                             sentiment=sentiment)
    
    @app.route('/api/email-analytics/export')
    @agency_required
    def api_export_email_analytics():
        """Exporte les analytics emails en CSV"""
        from services.email_sync.analytics import EmailAnalyticsService
        from datetime import datetime, timedelta
        import csv
        from io import StringIO
        
        if g.user.role != 'agency_admin':
            abort(403)
        
        # Récupérer les paramètres de période
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Dates par défaut (30 derniers jours)
        if not end_date_str:
            end_date = datetime.now().date()
        else:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        if not start_date_str:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        
        try:
            # Récupérer les analytics
            analytics = EmailAnalyticsService.get_comprehensive_analytics(
                g.agency.id,
                start_date,
                end_date
            )
            
            # Créer le CSV
            output = StringIO()
            writer = csv.writer(output)
            
            # En-têtes
            writer.writerow(['Métrique', 'Valeur'])
            writer.writerow([])
            
            # KPIs globaux
            writer.writerow(['=== STATISTIQUES GLOBALES ==='])
            writer.writerow(['Total emails', analytics.get('total_emails', 0)])
            writer.writerow(['Emails reçus', analytics.get('received_count', 0)])
            writer.writerow(['Emails envoyés', analytics.get('sent_count', 0)])
            writer.writerow(['Taux de réponse (%)', f"{analytics.get('response_rate', 0):.1f}"])
            writer.writerow(['Temps moyen de réponse', analytics.get('avg_response_time', '-')])
            writer.writerow(['Sans réponse', analytics.get('unanswered_count', 0)])
            writer.writerow([])
            
            # Top clients
            writer.writerow(['=== TOP 10 CLIENTS ==='])
            writer.writerow(['Client', 'Email', 'Nombre d\'emails'])
            for client in analytics.get('top_clients', []):
                writer.writerow([
                    client.get('name', ''),
                    client.get('email', ''),
                    client.get('count', 0)
                ])
            writer.writerow([])
            
            # Top sujets
            writer.writerow(['=== TOP 10 SUJETS ==='])
            writer.writerow(['Sujet', 'Occurrences'])
            for subject in analytics.get('top_subjects', []):
                writer.writerow([
                    subject.get('subject', ''),
                    subject.get('count', 0)
                ])
            
            # Préparer la réponse
            output.seek(0)
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename=email-analytics-{start_date}-{end_date}.csv'
            
            return response
            
        except Exception as e:
            app.logger.error(f"Erreur export analytics: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ==============================================================================
    # GESTION DES ERREURS
    # ==============================================================================
    
    @app.errorhandler(403)
    def forbidden(e):
        app.logger.warning(f"Accès refusé (403): {e} pour la route {request.path}")
        return jsonify({'error': 'Accès refusé', 'message': str(e)}), 403
    
    @app.errorhandler(404)
    def not_found(e):
        app.logger.warning(f"Ressource non trouvée (404): {e} pour la route {request.path}")
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
    with app.app_context():
        try:
            from services.email_sync.scheduler import init_scheduler
            from services.email_sync.background_tasks import set_socketio
            
            # Récupérer l'instance socketio depuis l'app
            socketio_instance = app.extensions.get('socketio')
            if socketio_instance:
                set_socketio(socketio_instance)
                app.logger.info("✅ SocketIO configured for background tasks")
            else:
                app.logger.warning("⚠️ SocketIO instance not found")
            
            init_scheduler(app)
            app.logger.info("✅ Email sync scheduler initialized")
        except Exception as e:
            app.logger.error(f"⚠️ Failed to initialize email scheduler: {e}")
    
    # Utiliser socketio.run au lieu de app.run pour supporter les websockets
    from flask_socketio import SocketIO as FlaskSocketIO
    # Récupérer l'instance socketio
    socketio_instance = app.extensions.get('socketio')
    if socketio_instance:
        socketio_instance.run(app, host='0.0.0.0', port=5000)
    else:
        app.run(host='0.0.0.0', port=5000)
