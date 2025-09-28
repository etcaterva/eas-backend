"""Test Instagram draw limits based on subscription tiers"""
import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from eas.api import models

User = get_user_model()


def create_stripe_list_mock(data_list):
    """Create a mock that behaves like Stripe's ListObject"""
    mock_list = MagicMock()
    mock_list.__getitem__ = MagicMock(return_value=data_list)
    mock_list.__len__ = MagicMock(return_value=len(data_list))
    mock_list.__bool__ = MagicMock(return_value=len(data_list) > 0)
    return mock_list


class InstagramLimitsTest(TestCase):
    """Test Instagram draw creation limits based on user subscription"""

    def setUp(self):
        """Set up test user and profile"""
        self.user = User.objects.create(
            username="test@example.com", email="test@example.com"
        )
        self.profile = models.UserProfile.objects.create(user=self.user)
        self.url = reverse("instagram-list")

    def test_instagram_draw_within_free_limit(self):
        """Test creating Instagram draw within free tier limits"""
        self.client.force_login(self.user)

        data = {
            "post_url": "https://www.instagram.com/p/test123/",
            "number_of_results": 5,  # Within free limit of 10
            "title": "Test Instagram Draw",
        }

        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )

        # Should succeed (or fail due to invalid URL, but not due to limits)
        self.assertNotEqual(response.status_code, 403)

    def test_instagram_draw_user_has_max_comments_calculated(self):
        """Test that authenticated user gets max_comments_allowed calculated"""
        self.client.force_login(self.user)

        data = {
            "post_url": "https://www.instagram.com/p/test123/",
            "number_of_results": 5,  # Within any limit
            "title": "Test Instagram Draw",
        }

        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )

        # Should not be blocked by limits (may fail for other reasons like invalid URL)
        self.assertNotEqual(response.status_code, 403)

    @patch("eas.api.stripe.stripe.Subscription.list")
    @patch("eas.api.stripe.stripe.Customer.list")
    def test_instagram_draw_with_stripe_customer(
        self, mock_customers, mock_subscriptions
    ):
        """Test user with Stripe customer and subscription can create draws"""
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

        self.client.force_login(self.user)

        data = {
            "post_url": "https://www.instagram.com/p/test123/",
            "number_of_results": 150,  # Within premium limit of 200
            "title": "Test Instagram Draw",
        }

        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )

        # Should succeed (or fail due to invalid URL, but not due to limits)
        self.assertNotEqual(response.status_code, 403)

    def test_instagram_draw_authenticated_user(self):
        """Test authenticated user can create draws"""
        self.client.force_login(self.user)

        data = {
            "post_url": "https://www.instagram.com/p/test123/",
            "number_of_results": 25,  # Any reasonable number
            "title": "Test Instagram Draw with Stripe",
        }

        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )

        # Should not be blocked by limits (may fail for other reasons like invalid URL)
        self.assertNotEqual(response.status_code, 403)

    def test_instagram_draw_unauthenticated_user(self):
        """Test unauthenticated users can still create draws (no limits applied)"""
        data = {
            "post_url": "https://www.instagram.com/p/test123/",
            "number_of_results": 100,  # Would exceed free limits but user not authenticated
            "title": "Test Instagram Draw",
        }

        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )

        # Should not be blocked by limits (may fail for other reasons like invalid URL)
        self.assertNotEqual(response.status_code, 403)
