# services/mailer.py
"""
Service d'envoi d'emails, capable de gérer des configurations SMTP par agence.
"""
from flask_mail import Mail, Message
from typing import Dict, Any


def send_manual_payment_email(
    app_mail: Mail,
    agency_mail_config: Dict[str, Any],
    agency_name: str,
    email_template: str,
    trip: Any,
    client: Any,
    amount: int
) -> None:
    """
    Envoie un email de demande de paiement manuel.

    Args:
        app_mail: L'instance Mail globale de l'application Flask.
        agency_mail_config: La configuration SMTP spécifique à l'agence.
        agency_name: Le nom de l'agence.
        email_template: Le template de l'email avec des placeholders.
        trip: L'objet Trip concerné.
        client: L'objet Client concerné.
        amount: Le montant de l'acompte.
    """
    if not client.email:
        raise ValueError("Le client n'a pas d'adresse email.")

    if not email_template:
        raise ValueError("Le template d'email pour le paiement manuel n'est pas configuré pour cette agence.")

    # Remplacer les placeholders dans le template
    subject = f"Instructions de paiement pour votre voyage à {trip.destination}"
    body = email_template.format(
        client_name=f"{client.first_name} {client.last_name}",
        trip_destination=trip.destination,
        amount=f"{amount}€",
        agency_name=agency_name
    )

    # Utiliser la configuration de l'agence si elle est complète, sinon la config globale
    mail_to_use = app_mail
    sender = agency_mail_config.get('sender') or app_mail.default_sender

    if all(k in agency_mail_config for k in ['server', 'port', 'username', 'password']):
        # Créer une instance Mail temporaire avec la configuration de l'agence
        temp_mail = Mail()
        temp_mail.init_app(app_mail.app)  # Utilise le contexte de l'app principale
        
        # Appliquer la config de l'agence
        app_mail.app.config['MAIL_SERVER'] = agency_mail_config['server']
        app_mail.app.config['MAIL_PORT'] = int(agency_mail_config['port'])
        app_mail.app.config['MAIL_USERNAME'] = agency_mail_config['username']
        app_mail.app.config['MAIL_PASSWORD'] = agency_mail_config['password']
        app_mail.app.config['MAIL_USE_TLS'] = agency_mail_config.get('use_tls', True)
        app_mail.app.config['MAIL_USE_SSL'] = agency_mail_config.get('use_ssl', False)
        
        mail_to_use = temp_mail

    # Créer et envoyer le message
    msg = Message(
        subject=subject,
        sender=sender,
        recipients=[client.email]
    )
    msg.body = body

    try:
        mail_to_use.send(msg)
        print(f"✅ Email de paiement manuel envoyé à {client.email}")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de l'email: {e}")
        # Ne pas bloquer le flux utilisateur, mais logger l'erreur est important
        raise