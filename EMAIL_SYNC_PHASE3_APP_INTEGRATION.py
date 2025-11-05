"""
Guide d'intégration Phase 3 dans app.py
Copiez et adaptez ces snippets dans votre fichier app.py
"""

# ==============================================================================
# 1. IMPORTS À AJOUTER EN HAUT DU FICHIER app.py
# ==============================================================================

# Phase 3A: Scheduler pour sync automatique
from services.email_sync.scheduler import init_scheduler, get_scheduler_status, trigger_manual_sync

# Phase 3B: Analytics emails
from services.email_sync.analytics import EmailAnalytics

# Phase 3C: Support Outlook
from services.email_sync.outlook_sync import OutlookSync

# Phase 3F: Recherche avancée
from services.email_sync.search import EmailSearch


# ==============================================================================
# 2. INITIALISATION DU SCHEDULER (dans le bloc if __name__ == '__main__')
# ==============================================================================

# À ajouter APRÈS la création de l'app mais AVANT app.run()
if __name__ == '__main__':
    with app.app_context():
        # Créer les tables si nécessaire
        db.create_all()
        
        # NOUVEAU: Initialiser le scheduler de sync email
        try:
            init_scheduler(app)
            print("✅ Email sync scheduler initialized")
        except Exception as e:
            print(f"⚠️ Failed to initialize email scheduler: {e}")
    
    # Démarrer l'application
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False') == '1'
    )


# ==============================================================================
# 3. ROUTES PHASE 3A: SYNCHRONISATION AUTOMATIQUE
# ==============================================================================

@app.route('/api/email/sync-now', methods=['POST'])
@login_required
@agency_required
def trigger_manual_email_sync():
    """Déclenche une synchronisation manuelle immédiate"""
    try:
        result = trigger_manual_sync(current_agency.id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error triggering manual sync: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/email/scheduler-status')
@login_required
@agency_admin_required
def get_email_scheduler_status():
    """Récupère le statut du scheduler"""
    try:
        status = get_scheduler_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/email/auto-sync-settings', methods=['POST'])
@login_required
@agency_admin_required
def update_auto_sync_settings():
    """Met à jour les paramètres de synchronisation automatique"""
    try:
        data = request.get_json()
        
        current_agency.auto_sync_enabled = data.get('enabled', False)
        current_agency.sync_frequency = data.get('frequency', 'hourly')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Paramètres de synchronisation automatique mis à jour'
        })
    except Exception as e:
        logger.error(f"Error updating auto-sync settings: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# 4. ROUTES PHASE 3B: ANALYTICS
# ==============================================================================

@app.route('/agency/email-analytics')
@login_required
@agency_required
def email_analytics_dashboard():
    """Dashboard d'analytics des emails"""
    return render_template(
        'agency/email-analytics.html',
        agency=current_agency,
        user=current_user
    )


@app.route('/api/email-analytics/metrics')
@login_required
@agency_required
def get_email_analytics_metrics():
    """Récupère les métriques d'analytics"""
    try:
        days = request.args.get('days', 30, type=int)
        
        analytics = EmailAnalytics(current_agency.id)
        
        # Métriques principales
        overview = analytics.get_overview_metrics(days)
        
        # Volume par jour
        volume_by_day = analytics.get_volume_by_day(days)
        
        # Distribution horaire
        hourly_dist = analytics.get_hourly_distribution(days)
        
        # Top clients
        top_clients = analytics.get_top_clients(days, limit=10)
        
        # Top sujets
        top_subjects = analytics.get_top_subjects(days, limit=10)
        
        return jsonify({
            'success': True,
            'overview': overview,
            'volume_by_day': volume_by_day,
            'hourly_distribution': hourly_dist,
            'top_clients': top_clients,
            'top_subjects': top_subjects
        })
    except Exception as e:
        logger.error(f"Error getting email analytics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/email-analytics/export')
@login_required
@agency_required
def export_email_analytics():
    """Exporte les analytics en CSV"""
    try:
        days = request.args.get('days', 30, type=int)
        
        analytics = EmailAnalytics(current_agency.id)
        csv_content = analytics.export_to_csv(days)
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=email_analytics_{current_agency.subdomain}_{days}days.csv'
            }
        )
    except Exception as e:
        logger.error(f"Error exporting email analytics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# 5. ROUTES PHASE 3C: OAUTH OUTLOOK
# ==============================================================================

@app.route('/oauth/outlook/authorize')
@login_required
@agency_admin_required
def outlook_oauth_authorize():
    """Redirige vers l'autorisation OAuth Outlook"""
    try:
        outlook_client_id = os.getenv('OUTLOOK_CLIENT_ID')
        outlook_client_secret = os.getenv('OUTLOOK_CLIENT_SECRET')
        outlook_tenant_id = os.getenv('OUTLOOK_TENANT_ID', 'common')
        
        if not outlook_client_id or not outlook_client_secret:
            flash('Les credentials Outlook ne sont pas configurés', 'error')
            return redirect(url_for('email_sync_settings'))
        
        # Créer le service Outlook temporaire pour l'auth
        outlook = OutlookSync(
            current_agency,
            outlook_client_id,
            outlook_client_secret,
            outlook_tenant_id
        )
        
        # Générer l'URL d'autorisation
        redirect_uri = url_for('outlook_oauth_callback', _external=True)
        state = secrets.token_urlsafe(32)
        session['outlook_oauth_state'] = state
        
        auth_url = outlook.get_authorization_url(redirect_uri, state)
        
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"Error initiating Outlook OAuth: {e}")
        flash(f'Erreur lors de l\'autorisation Outlook: {str(e)}', 'error')
        return redirect(url_for('email_sync_settings'))


@app.route('/oauth/outlook/callback')
@login_required
@agency_admin_required
def outlook_oauth_callback():
    """Callback OAuth Outlook"""
    try:
        # Vérifier le state pour la sécurité
        state = request.args.get('state')
        if state != session.get('outlook_oauth_state'):
            flash('État OAuth invalide', 'error')
            return redirect(url_for('email_sync_settings'))
        
        # Récupérer le code d'autorisation
        code = request.args.get('code')
        if not code:
            error = request.args.get('error', 'Unknown error')
            flash(f'Erreur OAuth: {error}', 'error')
            return redirect(url_for('email_sync_settings'))
        
        # Échanger le code contre des tokens
        outlook_client_id = os.getenv('OUTLOOK_CLIENT_ID')
        outlook_client_secret = os.getenv('OUTLOOK_CLIENT_SECRET')
        outlook_tenant_id = os.getenv('OUTLOOK_TENANT_ID', 'common')
        
        outlook = OutlookSync(
            current_agency,
            outlook_client_id,
            outlook_client_secret,
            outlook_tenant_id
        )
        
        redirect_uri = url_for('outlook_oauth_callback', _external=True)
        tokens = outlook.get_tokens_from_code(code, redirect_uri)
        
        if not tokens:
            flash('Échec de l\'obtention des tokens Outlook', 'error')
            return redirect(url_for('email_sync_settings'))
        
        # Récupérer les infos utilisateur
        user_info = outlook.get_user_info(tokens['access_token'])
        if not user_info:
            flash('Impossible de récupérer les informations utilisateur', 'error')
            return redirect(url_for('email_sync_settings'))
        
        # Sauvegarder les tokens (chiffrés)
        from utils.crypto import encrypt_api_key
        from datetime import timedelta
        
        current_agency.email_provider = 'outlook'
        current_agency.email_sync_enabled = True
        current_agency.email_access_token_encrypted = encrypt_api_key(tokens['access_token'])
        current_agency.email_refresh_token_encrypted = encrypt_api_key(tokens['refresh_token'])
        current_agency.email_token_expiry = datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))
        current_agency.email_sync_address = user_info.get('mail') or user_info.get('userPrincipalName')
        
        db.session.commit()
        
        flash('Synchronisation Outlook configurée avec succès !', 'success')
        return redirect(url_for('email_sync_settings'))
        
    except Exception as e:
        logger.error(f"Error in Outlook OAuth callback: {e}")
        flash(f'Erreur lors de la configuration Outlook: {str(e)}', 'error')
        return redirect(url_for('email_sync_settings'))


# ==============================================================================
# 6. ROUTES PHASE 3F: RECHERCHE AVANCÉE
# ==============================================================================

@app.route('/agency/email-search')
@login_required
@agency_required
def email_search_page():
    """Page de recherche d'emails"""
    return render_template(
        'agency/email-search.html',
        agency=current_agency,
        user=current_user
    )


@app.route('/api/email/search', methods=['POST'])
@login_required
@agency_required
def search_emails():
    """Recherche avancée d'emails"""
    try:
        data = request.get_json()
        
        search = EmailSearch(current_agency.id)
        
        # Convertir les dates si présentes
        date_from = None
        date_to = None
        
        if data.get('date_from'):
            date_from = datetime.strptime(data['date_from'], '%Y-%m-%d')
        
        if data.get('date_to'):
            date_to = datetime.strptime(data['date_to'], '%Y-%m-%d')
        
        # Effectuer la recherche
        results = search.search(
            query=data.get('query'),
            sender=data.get('sender'),
            recipient=data.get('recipient'),
            client_id=data.get('client_id'),
            date_from=date_from,
            date_to=date_to,
            is_outbound=data.get('is_outbound'),
            limit=data.get('limit', 100),
            offset=data.get('offset', 0)
        )
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error searching emails: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/email/thread/<thread_id>')
@login_required
@agency_required
def get_email_thread(thread_id):
    """Récupère tous les emails d'un thread"""
    try:
        search = EmailSearch(current_agency.id)
        result = search.get_thread(thread_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting email thread: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/email/suggested-filters')
@login_required
@agency_required
def get_suggested_email_filters():
    """Récupère des suggestions de filtres"""
    try:
        search = EmailSearch(current_agency.id)
        result = search.get_suggested_filters()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting suggested filters: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# 7. IMPORTS SUPPLÉMENTAIRES NÉCESSAIRES
# ==============================================================================

# À ajouter en haut du fichier si pas déjà présent:
# import secrets
# from flask import Response
# from datetime import datetime, timedelta


# ==============================================================================
# FIN DU GUIDE D'INTÉGRATION
# ==============================================================================

"""
NOTES D'IMPLÉMENTATION:

1. Copiez les imports en haut de app.py
2. Copiez l'initialisation du scheduler dans le bloc if __name__ == '__main__'
3. Copiez les routes nécessaires selon les fonctionnalités souhaitées
4. Testez chaque fonctionnalité après intégration
5. Exécutez la migration: flask db upgrade

ORDRE D'INTÉGRATION RECOMMANDÉ:
1. Phase 3A: Sync auto (routes + scheduler init)
2. Phase 3B: Analytics (routes + template)
3. Phase 3F: Recherche (routes + template)
4. Phase 3C: Outlook (routes OAuth)
"""
