import logging

import requests
from django.conf import settings

LOG = logging.getLogger(__name__)

PAYPAL_API_BASE_URL = (
    "https://api-m.sandbox.paypal.com"
    if settings.PAYPAL_MODE == "sandbox"
    else "https://api-m.paypal.com"
)


def get_paypal_access_token():
    auth_response = requests.post(
        f"{PAYPAL_API_BASE_URL}/v1/oauth2/token",
        headers={"Accept": "application/json", "Accept-Language": "en_US"},
        auth=(settings.PAYPAL_ID, settings.PAYPAL_SECRET),
        data={"grant_type": "client_credentials"},
    )
    auth_response.raise_for_status()
    return auth_response.json()["access_token"]


def create_payment(draw_url, accept_url, amount):
    access_token = get_paypal_access_token()
    payment_data = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {"currency_code": "EUR", "value": str(amount)},
                "description": f"Payment for {draw_url}",
            }
        ],
        "application_context": {
            "return_url": accept_url,
            "cancel_url": draw_url,
            "brand_name": "EchaloASuerte (EtCaterva)",
            "landing_page": "NO_PREFERENCE",
            "user_action": "PAY_NOW",
        },
    }
    response = requests.post(
        f"{PAYPAL_API_BASE_URL}/v2/checkout/orders",
        json=payment_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
    )
    response.raise_for_status()
    payment = response.json()
    redirect_url = next(
        link["href"] for link in payment["links"] if link["rel"] == "approve"
    )
    LOG.info("Created new payment with id %r and url %r", payment["id"], redirect_url)
    return payment["id"], redirect_url


def accept_payment(payment_id, payer_id):  # pragma: no cover
    access_token = get_paypal_access_token()
    response = requests.post(
        f"{PAYPAL_API_BASE_URL}/v2/checkout/orders/{payment_id}/capture",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        json={"payer_id": payer_id},
    )
    if response.status_code == 201:
        LOG.info("Payment[%s] execute successfully", payment_id)
    else:
        error = response.json()
        if error.get("name") == "INSTRUMENT_DECLINED":
            LOG.info("Payment[%s] declined", payment_id)
        else:
            LOG.error("Payment[%s] failed: %r", payment_id, error)
            raise Exception("Failed to process PayPal Payment")
