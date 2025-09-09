import logging

import stripe
from django.conf import settings

LOG = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_API_KEY


def create_payment(draw_url, accept_url, amount):
    """
    Creates a Stripe Checkout Session for payment.
    Returns (session_id, checkout_url)
    """
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "eur",
                    "product_data": {
                        "name": f"Payment for {draw_url}",
                    },
                    "unit_amount": int(amount * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=accept_url,
        cancel_url=accept_url,
    )
    LOG.info(
        "Created Stripe payment session with id %r and url %r", session.id, session.url
    )
    return session.id, session.url


def accept_payment(payment_id):
    """
    Checks if the Stripe Checkout Session is completed.
    Returns True if payment is completed, False otherwise.
    """
    session = stripe.checkout.Session.retrieve(payment_id)
    status = session.payment_status
    LOG.info("Stripe payment session %s is in status %s", payment_id, status)
    return status == "paid"
