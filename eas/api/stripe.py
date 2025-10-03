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


def get_user_tier_from_profile(user_profile):
    """
    Helper function to get user tier, integrating with Stripe.

    Args:
        user_profile: UserProfile instance

    Returns:
        str: tier name ('free', 'starter', 'creator', 'agency')
    """
    # Simply use the email-based function
    return get_user_tier_from_email(user_profile.user.email)


def get_user_tier_from_email(email):
    """
    Get user tier directly from email by looking up their Stripe customer.

    Args:
        email: User's email address

    Returns:
        str: tier name ('free', 'starter', 'creator', 'agency')
    """
    # Search for customer by email
    customers = stripe.Customer.list(email=email, limit=1)

    # Check if any customers were found
    if not customers or len(customers["data"]) == 0:
        LOG.info("No Stripe customer found for email: %s", email)
        return "free"

    customer = customers["data"][0]
    LOG.info("Found Stripe customer %s for email: %s", customer.id, email)

    # Get active subscriptions for this customer
    subscriptions = stripe.Subscription.list(
        customer=customer.id, status="active", limit=1
    )

    # Check if any active subscriptions were found
    if not subscriptions or len(subscriptions["data"]) == 0:
        LOG.info("No active subscriptions found for customer %s", customer.id)
        return "free"

    subscription = subscriptions["data"][0]
    LOG.info(
        "Found active subscription %s for customer %s",
        subscription["id"],
        customer.id,
    )

    # Get the price from the first subscription item
    if subscription["items"] and len(subscription["items"]["data"]) > 0:
        price = subscription["items"]["data"][0]["price"]
        LOG.info(
            "Found price %s for subscription %s",
            price["lookup_key"],
            subscription["id"],
        )
        return map_price_to_tier(price["lookup_key"])
    else:  # pragma: no cover
        LOG.warning("No subscription found for subscription %s", subscription["id"])
        return "free"


def map_price_to_tier(lookup_key):
    """
    Map Stripe price lookup_key to our internal tier system using settings configuration.

    Args:
        lookup_key: Stripe price lookup_key

    Returns:
        str: tier name ('free', 'starter', 'creator', 'agency')
    """
    if not lookup_key:
        return "free"

    # Check each tier in settings to find matching lookup_key
    for tier_name, tier_config in settings.SUBSCRIPTION_TIERS.items():
        if lookup_key in tier_config.get("lookup_keys", []):
            LOG.info("Mapped lookup_key %s to tier %s", lookup_key, tier_name)
            return tier_name

    # If we can't find the lookup_key in our configuration, log an error and default to free
    LOG.error(
        "Unknown lookup_key '%s' not found in SUBSCRIPTION_TIERS configuration. Defaulting to 'free' tier.",
        lookup_key,
    )
    return "free"


def create_subscription(success_url, draw_url, lookup_key):
    """
    Create a Stripe subscription checkout session.

    Args:
        success_url: URL to redirect on successful subscription
        draw_url: Draw URL to store in metadata for later redirection
        lookup_key: Stripe price lookup_key for the subscription

    Returns:
        tuple: (session_id, checkout_url)

    Raises:
        ValueError: If no price found for lookup_key
    """
    # Find the price using lookup_key
    prices = stripe.Price.list(lookup_keys=[lookup_key])
    if not prices or len(prices["data"]) == 0:
        raise ValueError(f"No price found for lookup_key: {lookup_key}")

    price = prices["data"][0]
    LOG.info("Found price %s for lookup_key %s", price["id"], lookup_key)

    # Create checkout session
    session = stripe.checkout.Session.create(
        mode="subscription",
        success_url=success_url,
        line_items=[
            {
                "price": price["id"],
                "quantity": 1,
            }
        ],
        metadata={
            "draw_url": draw_url,
        },
    )

    LOG.info("Created subscription session %s with draw_url in metadata", session.id)
    return session.id, session.url


def accept_subscription(session_id):
    """
    Check if the Stripe subscription checkout session is completed and active.

    Args:
        session_id: Stripe checkout session ID

    Returns:
        False if subscription is not active, or tuple (draw_url, email) if active
    """
    session = stripe.checkout.Session.retrieve(session_id)

    if session.mode != "subscription":
        LOG.warning("Session %s is not a subscription session", session_id)
        return False

    if not session.subscription:
        LOG.info("No subscription found for session %s", session_id)
        return False

    # Get the subscription details
    subscription = stripe.Subscription.retrieve(session.subscription)
    LOG.info("Subscription %s status: %s", subscription.id, subscription.status)

    if subscription.status != "active":
        return False

    # Only extract metadata and email if subscription is active
    draw_url = session.metadata.get("draw_url", "") if session.metadata else ""
    email = session.customer_details.email if session.customer_details else ""

    return draw_url, email


def create_customer_portal_session(email):
    """
    Create a Stripe Customer Portal session for a customer.

    Args:
        email: Customer's email address to lookup their Stripe customer

    Returns:
        str: Customer portal URL, or None if customer not found
    """
    customers = stripe.Customer.list(email=email, limit=1)
    if not customers or len(customers["data"]) == 0:
        LOG.info("No Stripe customer found for email: %s", email)
        return None
    customer = customers["data"][0]
    LOG.info("Found Stripe customer %s for email: %s", customer.id, email)
    session_params = {
        "customer": customer.id,
    }
    session = stripe.billing_portal.Session.create(**session_params)
    LOG.info(
        "Created customer portal session %s for customer %s", session.id, customer.id
    )
    return session.url
