import logging

import requests
from django.conf import settings

LOG = logging.getLogger(__name__)

REVOLUT_API_V = "2024-09-01"
REVOLUT_API_BASE_URL = (
    "https://sandbox-merchant.revolut.com"
    if settings.REVOLUT_MODE == "sandbox"
    else "https://merchant.revolut.com"
)

bearer = settings.REVOLUT_SECRET


def create_payment(draw_url, accept_url, amount):
    url = f"{REVOLUT_API_BASE_URL}/api/orders"
    payload = {
        "amount": amount * 100,
        "currency": "EUR",
        "description": f"Payment for {draw_url}",
        "redirect_url": accept_url,
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Revolut-Api-Version": REVOLUT_API_V,
        "Authorization": f"Bearer {bearer}",
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    payment = response.json()
    redirect_url = payment["checkout_url"]
    LOG.info("Created new payment with id %r and url %r", payment["id"], redirect_url)
    return payment["id"], redirect_url


def accept_payment(payment_id):
    url = f"{REVOLUT_API_BASE_URL}/api/orders/{payment_id}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Revolut-Api-Version": REVOLUT_API_V,
        "Authorization": f"Bearer {bearer}",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    status = response.json()["state"]
    LOG.info("Payment with id %s is in status %s", payment_id, status)
    return status == "completed"
