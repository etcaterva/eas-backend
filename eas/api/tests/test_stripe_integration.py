"""Test Stripe integration functionality"""
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from eas.api import models, stripe

User = get_user_model()


def create_stripe_list_mock(data_list):
    """Create a mock that behaves like Stripe's ListObject"""
    mock_list = MagicMock()
    mock_list.__getitem__ = MagicMock(return_value=data_list)
    mock_list.__len__ = MagicMock(return_value=len(data_list))
    mock_list.__bool__ = MagicMock(return_value=len(data_list) > 0)
    return mock_list


class StripeIntegrationTest(TestCase):
    """Test Stripe integration functions"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            username="test@example.com", email="test@example.com"
        )
        self.profile = models.UserProfile.objects.create(user=self.user)

    @patch("eas.api.stripe.stripe.Customer.list")
    def test_get_user_tier_from_profile_no_stripe_customer(self, mock_customers):
        """Test getting tier for user without Stripe customer"""
        profile_no_stripe = models.UserProfile.objects.create(
            user=User.objects.create(
                username="nostripe@example.com", email="nostripe@example.com"
            )
        )

        # Mock empty customer list response
        mock_customers.return_value = create_stripe_list_mock([])

        tier = stripe.get_user_tier_from_profile(profile_no_stripe)
        self.assertEqual(tier, "free")

    @patch("eas.api.stripe.stripe.Subscription.list")
    @patch("eas.api.stripe.stripe.Customer.list")
    def test_get_user_tier_from_profile_no_active_subscription(
        self, mock_customers, mock_subscriptions
    ):
        """Test getting tier for user with no active subscription"""
        # Mock customer object
        mock_customer = MagicMock()
        mock_customer.id = "cus_test123"

        # Mock customer list response
        mock_customers.return_value = create_stripe_list_mock([mock_customer])

        # Mock empty subscription list response
        mock_subscriptions.return_value = create_stripe_list_mock([])

        tier = stripe.get_user_tier_from_profile(self.profile)
        self.assertEqual(tier, "free")
        mock_customers.assert_called_once_with(email="test@example.com", limit=1)
        mock_subscriptions.assert_called_once_with(
            customer="cus_test123", status="active", limit=1
        )

    @patch("eas.api.stripe.stripe.Subscription.list")
    @patch("eas.api.stripe.stripe.Customer.list")
    def test_get_user_tier_from_profile_with_starter_subscription(
        self, mock_customers, mock_subscriptions
    ):
        """Test getting tier for user with starter subscription"""
        # Mock customer object
        mock_customer = MagicMock()
        mock_customer.id = "cus_test123"

        # Mock customer list response
        mock_customers.return_value = create_stripe_list_mock([mock_customer])

        # Mock price object as dictionary
        mock_price = {"lookup_key": "starter_monthly"}

        # Mock subscription item as dictionary
        mock_item = {"price": mock_price}

        # Mock subscription object as dictionary
        mock_subscription = {
            "id": "sub_starter123",
            "items": create_stripe_list_mock([mock_item]),
        }

        # Mock subscription list response
        mock_subscriptions.return_value = create_stripe_list_mock([mock_subscription])

        tier = stripe.get_user_tier_from_profile(self.profile)
        self.assertEqual(tier, "starter")

    @patch("eas.api.stripe.stripe.Subscription.list")
    @patch("eas.api.stripe.stripe.Customer.list")
    def test_get_user_tier_from_email_with_subscription(
        self, mock_customers, mock_subscriptions
    ):
        """Test getting tier directly from email with active subscription"""
        # Mock customer object
        mock_customer = MagicMock()
        mock_customer.id = "cus_email_test"

        # Mock customer list response
        mock_customers.return_value = create_stripe_list_mock([mock_customer])

        # Mock price object as dictionary
        mock_price = {"lookup_key": "creator_monthly"}

        # Mock subscription item as dictionary
        mock_item = {"price": mock_price}

        # Mock subscription object as dictionary
        mock_subscription = {
            "id": "sub_test123",
            "items": create_stripe_list_mock([mock_item]),
        }

        # Mock subscription list response
        mock_subscriptions.return_value = create_stripe_list_mock([mock_subscription])

        tier = stripe.get_user_tier_from_email("test@example.com")
        self.assertEqual(tier, "creator")

        mock_customers.assert_called_once_with(email="test@example.com", limit=1)
        mock_subscriptions.assert_called_once_with(
            customer="cus_email_test", status="active", limit=1
        )

    @patch("eas.api.stripe.stripe.Customer.list")
    def test_get_user_tier_from_email_no_customer(self, mock_customers):
        """Test getting tier from email when no Stripe customer exists"""
        # Mock empty customer list response
        mock_customers.return_value = create_stripe_list_mock([])

        tier = stripe.get_user_tier_from_email("nonexistent@example.com")
        self.assertEqual(tier, "free")

    def testmap_price_to_tier_patterns(self):
        """Test price lookup_key to tier mapping using configured lookup_keys"""
        # Test starter tier - using lookup_keys from settings
        self.assertEqual(stripe.map_price_to_tier("starter_monthly"), "starter")
        self.assertEqual(stripe.map_price_to_tier("starter_yearly"), "starter")

        # Test creator tier
        self.assertEqual(stripe.map_price_to_tier("creator_monthly"), "creator")
        self.assertEqual(stripe.map_price_to_tier("creator_yearly"), "creator")

        # Test agency tier
        self.assertEqual(stripe.map_price_to_tier("agency_monthly"), "agency")
        self.assertEqual(stripe.map_price_to_tier("agency_yearly"), "agency")

        # Test unknown lookup_key defaults to free
        self.assertEqual(stripe.map_price_to_tier("unknown_plan"), "free")

        # Test empty/None lookup_key defaults to free
        self.assertEqual(stripe.map_price_to_tier(""), "free")
        self.assertEqual(stripe.map_price_to_tier(None), "free")

    def test_map_price_to_tier_edge_cases(self):
        """Test edge cases for price to tier mapping"""
        # Test that unknown lookup_key returns free
        self.assertEqual(stripe.map_price_to_tier("unknown_123"), "free")

        # Test that configured lookup_keys work correctly
        self.assertEqual(stripe.map_price_to_tier("starter_monthly"), "starter")
        self.assertEqual(stripe.map_price_to_tier("creator_yearly"), "creator")

    @patch("eas.api.stripe.stripe.checkout.Session.create")
    @patch("eas.api.stripe.stripe.Price.list")
    def test_create_subscription_success(self, mock_price_list, mock_session_create):
        """Test successful subscription creation"""
        # Mock price lookup
        mock_price = {"id": "price_123", "lookup_key": "starter_monthly"}
        mock_price_list.return_value = create_stripe_list_mock([mock_price])

        # Mock session creation
        mock_session = MagicMock()
        mock_session.id = "cs_test_123"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_123"
        mock_session_create.return_value = mock_session

        # Test the function
        session_id, checkout_url = stripe.create_subscription(
            "https://example.com/success",
            "https://example.com/draw/123",
            "starter_monthly",
        )

        # Verify results
        self.assertEqual(session_id, "cs_test_123")
        self.assertEqual(checkout_url, "https://checkout.stripe.com/pay/cs_test_123")

        # Verify API calls
        mock_price_list.assert_called_once_with(lookup_keys=["starter_monthly"])
        mock_session_create.assert_called_once_with(
            mode="subscription",
            success_url="https://example.com/success",
            line_items=[
                {
                    "price": "price_123",
                    "quantity": 1,
                }
            ],
            metadata={
                "draw_url": "https://example.com/draw/123",
            },
        )

    @patch("eas.api.stripe.stripe.Price.list")
    def test_create_subscription_price_not_found(self, mock_price_list):
        """Test create_subscription with invalid lookup_key"""
        # Mock empty price list
        mock_price_list.return_value = create_stripe_list_mock([])

        with self.assertRaises(ValueError) as context:
            stripe.create_subscription(
                "https://example.com/success",
                "https://example.com/draw/123",
                "nonexistent_key",
            )

        self.assertIn(
            "No price found for lookup_key: nonexistent_key", str(context.exception)
        )

    @patch("eas.api.stripe.stripe.Subscription.retrieve")
    @patch("eas.api.stripe.stripe.checkout.Session.retrieve")
    def test_accept_subscription_active(
        self, mock_session_retrieve, mock_subscription_retrieve
    ):
        """Test accept_subscription with active subscription"""
        # Mock checkout session
        mock_session = MagicMock()
        mock_session.mode = "subscription"
        mock_session.subscription = "sub_123"
        mock_session.metadata = {"draw_url": "https://example.com/draw/123"}
        mock_session.customer_details.email = "test@example.com"
        mock_session_retrieve.return_value = mock_session

        # Mock active subscription
        mock_subscription = MagicMock()
        mock_subscription.id = "sub_123"
        mock_subscription.status = "active"
        mock_subscription_retrieve.return_value = mock_subscription

        result = stripe.accept_subscription("cs_test_123")

        # Should return tuple with draw_url and email
        self.assertIsInstance(result, tuple)
        draw_url, email = result
        self.assertEqual(draw_url, "https://example.com/draw/123")
        self.assertEqual(email, "test@example.com")

    @patch("eas.api.stripe.stripe.Subscription.retrieve")
    @patch("eas.api.stripe.stripe.checkout.Session.retrieve")
    def test_accept_subscription_inactive(
        self, mock_session_retrieve, mock_subscription_retrieve
    ):
        """Test accept_subscription with inactive subscription"""
        # Mock checkout session
        mock_session = MagicMock()
        mock_session.mode = "subscription"
        mock_session.subscription = "sub_123"
        mock_session_retrieve.return_value = mock_session

        # Mock inactive subscription
        mock_subscription = MagicMock()
        mock_subscription.id = "sub_123"
        mock_subscription.status = "incomplete"
        mock_subscription_retrieve.return_value = mock_subscription

        result = stripe.accept_subscription("cs_test_123")
        self.assertFalse(result)

    @patch("eas.api.stripe.stripe.checkout.Session.retrieve")
    def test_accept_subscription_not_subscription_mode(self, mock_session_retrieve):
        """Test accept_subscription with payment mode session"""
        # Mock payment session (not subscription)
        mock_session = MagicMock()
        mock_session.mode = "payment"
        mock_session_retrieve.return_value = mock_session

        result = stripe.accept_subscription("cs_test_123")
        self.assertFalse(result)

    @patch("eas.api.stripe.stripe.checkout.Session.retrieve")
    def test_accept_subscription_no_subscription(self, mock_session_retrieve):
        """Test accept_subscription with session without subscription"""
        # Mock subscription session without subscription
        mock_session = MagicMock()
        mock_session.mode = "subscription"
        mock_session.subscription = None
        mock_session_retrieve.return_value = mock_session

        result = stripe.accept_subscription("cs_test_123")
        self.assertFalse(result)
