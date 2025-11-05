"""
Email Sync Scheduler - Phase 3A
Gestion de la planification des synchronisations automatiques
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from services.email_sync.background_tasks import sync_all_agencies, check_and_notify_errors

logger = logging.getLogger(__name__)

# Instance globale du scheduler
_scheduler = None


def get_scheduler():
    """Retourne l'instance globale du scheduler"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            daemon=True,
            timezone='UTC'
        )
    return _scheduler


def init_scheduler(app):
    """
    Initialise et démarre le scheduler de synchronisation.
    
    Args:
        app: Instance Flask app (pour le contexte)
    """
    global _scheduler
    
    if _scheduler is not None:
        logger.warning("Scheduler already initialized")
        return _scheduler
    
    try:
        scheduler = get_scheduler()
        
        # Job 1: Synchronisation toutes les 3 minutes
        # Ce job vérifie toutes les agences et synchronise selon leur fréquence configurée
        scheduler.add_job(
            func=lambda: run_with_app_context(app, sync_all_agencies),
            trigger=IntervalTrigger(minutes=3),
            id='sync_all_agencies_frequent',
            name='Sync all agencies emails (every 3 minutes)',
            replace_existing=True
        )
        logger.info("Added job: sync_all_agencies_frequent (every 3 minutes)")
        
        # Job 2: Vérification des erreurs toutes les 6 heures
        scheduler.add_job(
            func=lambda: run_with_app_context(app, check_and_notify_errors),
            trigger=IntervalTrigger(hours=6),
            id='check_sync_errors',
            name='Check and notify sync errors',
            replace_existing=True
        )
        logger.info("Added job: check_sync_errors")
        
        # Job 3: Synchronisation quotidienne à 2h du matin
        # Pour les agences configurées en mode 'daily'
        scheduler.add_job(
            func=lambda: run_with_app_context(app, sync_daily_agencies),
            trigger=CronTrigger(hour=2, minute=0),
            id='sync_daily_agencies',
            name='Sync daily agencies at 2 AM',
            replace_existing=True
        )
        logger.info("Added job: sync_daily_agencies")
        
        # Démarrer le scheduler
        scheduler.start()
        logger.info("Email sync scheduler started successfully")
        
        return scheduler
        
    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {str(e)}", exc_info=True)
        raise


def run_with_app_context(app, func):
    """
    Exécute une fonction dans le contexte de l'application Flask.
    
    Args:
        app: Instance Flask app
        func: Fonction à exécuter
    """
    with app.app_context():
        try:
            result = func()
            logger.info(f"Job {func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Job {func.__name__} failed: {str(e)}", exc_info=True)
            raise


def sync_daily_agencies():
    """
    Synchronise uniquement les agences configurées en mode 'daily'.
    Cette fonction est appelée par le job quotidien à 2h du matin.
    """
    from models import Agency
    from services.email_sync.background_tasks import sync_agency_emails
    
    logger.info("Starting daily sync for agencies with 'daily' frequency")
    
    try:
        agencies = Agency.query.filter_by(
            email_sync_enabled=True,
            auto_sync_enabled=True,
            sync_frequency='daily'
        ).all()
        
        if not agencies:
            logger.info("No agencies configured for daily sync")
            return {
                'success': True,
                'agencies_count': 0,
                'message': 'No agencies to sync'
            }
        
        logger.info(f"Found {len(agencies)} agencies for daily sync")
        
        results = []
        for agency in agencies:
            result = sync_agency_emails(agency.id)
            results.append({
                'agency_id': agency.id,
                'agency_name': agency.name,
                'success': result.get('success', False),
                'new_emails': result.get('new_emails', 0)
            })
        
        return {
            'success': True,
            'agencies_count': len(agencies),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error in sync_daily_agencies: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def stop_scheduler():
    """Arrête le scheduler"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("Email sync scheduler stopped")


def get_scheduler_status():
    """
    Retourne le statut du scheduler et ses jobs.
    
    Returns:
        dict: Informations sur le scheduler
    """
    global _scheduler
    
    if _scheduler is None:
        return {
            'running': False,
            'jobs': []
        }
    
    jobs = []
    for job in _scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': next_run.strftime('%Y-%m-%d %H:%M:%S UTC') if next_run else 'N/A'
        })
    
    return {
        'running': _scheduler.running,
        'jobs': jobs
    }


def trigger_manual_sync(agency_id: int = None):
    """
    Déclenche une synchronisation manuelle immédiate.
    
    Args:
        agency_id: Si fourni, synchronise uniquement cette agence, sinon toutes
        
    Returns:
        dict: Résultats de la synchronisation
    """
    from services.email_sync.background_tasks import sync_agency_emails, sync_all_agencies
    
    try:
        if agency_id:
            logger.info(f"Triggering manual sync for agency {agency_id}")
            return sync_agency_emails(agency_id)
        else:
            logger.info("Triggering manual sync for all agencies")
            return sync_all_agencies()
            
    except Exception as e:
        logger.error(f"Error in trigger_manual_sync: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
