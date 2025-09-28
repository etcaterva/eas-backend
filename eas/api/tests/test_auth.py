"""Test authentication functionality"""
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


class AuthenticationTest(TestCase):
    """Test user authentication with magic links"""

    @patch("eas.api.email.boto3.client")
    def test_request_magic_link_existing_user(self, mock_boto_client):
        """Test requesting magic link for existing user"""
        # Mock SES client
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {"MessageId": "test-message-id"}
        mock_boto_client.return_value = mock_ses

        user = User.objects.create(
            username="test@example.com", email="test@example.com"
        )

        url = reverse("request-magic-link")
        data = {
            "email": "test@example.com",
            "return_url": "https://example.com/success",
        }

        response = self.client.post(
            url, data=json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(models.LoginToken.objects.filter(user=user).exists())

    @patch("eas.api.email.boto3.client")
    def test_request_magic_link_nonexistent_user(self, mock_boto_client):
        """Test requesting magic link for non-existent user creates the user"""
        # Mock SES client
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {"MessageId": "test-message-id"}
        mock_boto_client.return_value = mock_ses

        url = reverse("request-magic-link")
        data = {
            "email": "nonexistent@example.com",
            "return_url": "https://example.com/success",
        }

        # Verify user doesn't exist initially
        self.assertFalse(User.objects.filter(email="nonexistent@example.com").exists())

        response = self.client.post(
            url, data=json.dumps(data), content_type="application/json"
        )

        # Should succeed and create the user
        self.assertEqual(response.status_code, 200)

        # Verify user was created
        self.assertTrue(User.objects.filter(email="nonexistent@example.com").exists())

        # Verify a token was created for the new user
        new_user = User.objects.get(email="nonexistent@example.com")
        self.assertTrue(new_user.logintoken_set.exists())

    def test_verify_magic_link(self):
        """Test verifying magic link logs user in"""
        # Create user and token manually
        user = User.objects.create(
            username="test@example.com", email="test@example.com"
        )
        models.UserProfile.objects.create(user=user)
        return_url = "https://example.com/success"
        login_token = models.LoginToken.create_for_user(user, return_url=return_url)

        # Verify the token (should redirect to return_url)
        verify_url = reverse("verify-magic-link")
        response = self.client.get(f"{verify_url}?token={login_token.token}")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, return_url)

        # Token should be deleted after use
        self.assertFalse(models.LoginToken.objects.filter(id=login_token.id).exists())

    @patch("eas.api.stripe.stripe.Customer.list")
    def test_current_user_authenticated(self, mock_customer_list):
        """Test getting current user info when authenticated"""
        # Mock Stripe customer list to return empty (free tier)
        mock_customer_list.return_value = create_stripe_list_mock([])

        user = User.objects.create(
            username="test@example.com", email="test@example.com"
        )
        models.UserProfile.objects.create(user=user)

        self.client.force_login(user)

        url = reverse("current-user")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["user"]["email"], "test@example.com")
        self.assertEqual(
            response_data["user"]["tier"], "free"
        )  # User without Stripe subscription should be 'free'
        self.assertIn("tier", response_data["user"])
        self.assertNotIn("id", response_data["user"])  # ID should not be present

    @patch("eas.api.stripe.stripe.Subscription.list")
    @patch("eas.api.stripe.stripe.Customer.list")
    def test_current_user_with_stripe_subscription(
        self, mock_customers, mock_subscriptions
    ):
        """Test getting current user info when user has Stripe subscription"""
        user = User.objects.create(
            username="premium@example.com", email="premium@example.com"
        )
        models.UserProfile.objects.create(user=user)

        # Mock customer object
        mock_customer = MagicMock()
        mock_customer.id = "cus_premium_test"

        # Mock customer list response
        mock_customers.return_value = create_stripe_list_mock([mock_customer])

        # Mock price object as dictionary
        mock_price = {"lookup_key": "creator_monthly"}

        # Mock subscription item as dictionary
        mock_item = {"price": mock_price}

        # Mock subscription object as dictionary
        mock_subscription = {
            "id": "sub_creator123",
            "items": create_stripe_list_mock([mock_item]),
        }

        # Mock subscription list response
        mock_subscriptions.return_value = create_stripe_list_mock([mock_subscription])

        self.client.force_login(user)

        url = reverse("current-user")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["user"]["email"], "premium@example.com")
        self.assertEqual(
            response_data["user"]["tier"], "creator"
        )  # User with creator subscription
        self.assertNotIn("id", response_data["user"])  # ID should not be present

    def test_current_user_not_authenticated(self):
        """Test getting current user info when not authenticated"""
        url = reverse("current-user")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "Not authenticated")

    def test_user_profile_model(self):
        """Test user profile model functionality"""
        user = User.objects.create(
            username="test@example.com", email="test@example.com"
        )

        # Test profile creation
        profile = models.UserProfile.objects.create(user=user)
        self.assertEqual(profile.user, user)
        self.assertEqual(str(profile), user.email)

    def test_subscription_tiers_endpoint(self):
        """Test the subscription tiers information endpoint"""
        url = reverse("subscription-tiers")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("tiers", data)

        tiers = data["tiers"]
        self.assertIn("free", tiers)
        self.assertIn("starter", tiers)
        self.assertIn("creator", tiers)
        self.assertIn("agency", tiers)

        # Check structure of tier data
        self.assertEqual(tiers["free"]["max_instagram_comments"], 300)
        self.assertEqual(tiers["starter"]["max_instagram_comments"], 2000)
        self.assertEqual(tiers["creator"]["max_instagram_comments"], 5000)
        self.assertEqual(tiers["agency"]["max_instagram_comments"], 2147483647)

    def test_request_magic_link_missing_return_url(self):
        """Test requesting magic link without return_url should fail"""
        url = reverse("request-magic-link")
        data = {"email": "test@example.com"}

        response = self.client.post(
            url, data=json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data["error"], "Return URL is required")
