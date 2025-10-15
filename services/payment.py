# services/payment.py
"""
Service de gestion des paiements avec Stripe.
"""
import stripe
from typing import Dict


def create_stripe_payment_link(trip_name: str, amount: int, stripe_api_key: str, success_url: str) -> str:
    """
    Crée un produit, un prix et un lien de paiement dans Stripe.

    Args:
        trip_name (str): Le nom du voyage, qui sera le nom du produit sur Stripe.
        amount (int): Le montant de l'acompte en centimes (ex: 10000 pour 100.00€).
        stripe_api_key (str): La clé API Stripe secrète de l'agence.
        success_url (str): L'URL de redirection après un paiement réussi.

    Returns:
        str: L'URL du lien de paiement généré.
    
    Raises:
        ValueError: Si la configuration Stripe est invalide.
        Exception: Pour toute autre erreur de l'API Stripe.
    """
    if not stripe_api_key:
        raise ValueError("La clé API Stripe est manquante.")

    stripe.api_key = stripe_api_key

    try:
        # 1. Créer un produit sur Stripe pour ce voyage
        product = stripe.Product.create(name=f"Acompte - {trip_name}")

        # 2. Créer un prix pour ce produit
        price = stripe.Price.create(
            product=product.id,
            unit_amount=amount,
            currency='eur',
        )

        # 3. Créer un lien de paiement pour ce prix
        payment_link = stripe.PaymentLink.create(
            line_items=[{"price": price.id, "quantity": 1}],
            after_completion={
                'type': 'redirect',
                'redirect': {'url': success_url},
            },
        )

        return payment_link.url

    except Exception as e:
        print(f"❌ Erreur de création du lien de paiement Stripe: {e}")
        raise