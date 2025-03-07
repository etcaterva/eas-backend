import logging

import paypalrestsdk
from django.conf import settings

LOG = logging.getLogger(__name__)


def setup_paypal():
    paypalrestsdk.configure(
        {
            "mode": settings.PAYPAL_MODE,  # sandbox or live
            "client_id": settings.PAYPAL_ID,
            "client_secret": settings.PAYPAL_SECRET,
        }
    )
    setup_paypal.__code__ = (lambda: None).__code__  # run once


def create_payment(
    draw_url,
    accept_url,
    ammount,
):
    setup_paypal()
    payment = paypalrestsdk.Payment(
        {
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": accept_url,
                "cancel_url": draw_url,
            },
            "transactions": [
                {
                    "amount": {"total": str(ammount), "currency": "EUR"},
                    "description": draw_url,
                }
            ],
        }
    )
    try:
        payment.create()
        (redirect_url,) = [
            link.href for link in payment.links if link.method == "REDIRECT"
        ]
    except Exception:  # pragma: no cover
        LOG.info("Failed to create paypal payment", exc_info=True)
        raise
    else:
        LOG.info("Created new payment with id %r and url %r", payment.id, redirect_url)
    return payment.id, redirect_url


def accept_payment(payment_id, payer_id):  # pragma: no cover
    setup_paypal()
    payment = paypalrestsdk.Payment.find(payment_id)
    if payment.execute({"payer_id": payer_id}):
        LOG.info("Payment[%s] execute successfully", payment.id)
    elif (
        getattr(payment, "error") is not None
        and payment.error.get("name") == "INSTRUMENT_DECLINED"
    ):
        LOG.info("Payment[%s] declined", payment.id)
    else:
        LOG.error("Payment[%s] failed: %r", payment.id, payment.error)
        raise Exception("Failed to process PayPal Payment")
