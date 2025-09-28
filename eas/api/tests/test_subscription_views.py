"""Test subscription view endpoints"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from eas.api import models

User = get_user_model()


class SubscriptionViewsTest(TestCase):
    """Test subscription-related view endpoints"""

    def setUp(self):
        """Set up test data"""
        self.create_subscription_url = reverse("create-subscription")
        self.accept_subscription_url = reverse("accept-subscription")

    def test_create_subscription_missing_subscription_key(self):
        """Test create_subscription with missing subscription_key"""
        response = self.client.post(
            self.create_subscription_url,
            {"draw_url": "https://example.com/draw/123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "subscription_key is required")

    def test_create_subscription_missing_draw_url(self):
        """Test create_subscription with missing draw_url"""
        response = self.client.post(
            self.create_subscription_url,
            {"subscription_key": "starter_monthly"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "draw_url is required")

    def test_create_subscription_invalid_subscription_key(self):
        """Test create_subscription with invalid subscription_key"""
        response = self.client.post(
            self.create_subscription_url,
            {
                "subscription_key": "invalid_key",
                "draw_url": "https://example.com/draw/123",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid subscription_key", response.json()["error"])

    @patch("eas.api.stripe.create_subscription")
    def test_create_subscription_success(self, mock_create_subscription):
        """Test successful subscription creation"""
        # Mock Stripe response
        mock_create_subscription.return_value = (
            "cs_test_123",
            "https://checkout.stripe.com/pay/cs_test_123",
        )

        response = self.client.post(
            self.create_subscription_url,
            {
                "subscription_key": "starter_monthly",
                "draw_url": "https://example.com/draw/123",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["session_id"], "cs_test_123")
        self.assertEqual(
            data["checkout_url"], "https://checkout.stripe.com/pay/cs_test_123"
        )

        # Verify Stripe was called with correct parameters
        mock_create_subscription.assert_called_once()
        args = mock_create_subscription.call_args[1]
        self.assertEqual(args["lookup_key"], "starter_monthly")
        self.assertEqual(args["draw_url"], "https://example.com/draw/123")
        self.assertIn("session_id={CHECKOUT_SESSION_ID}", args["success_url"])

    @patch("eas.api.stripe.create_subscription")
    def test_create_subscription_stripe_error(self, mock_create_subscription):
        """Test create_subscription with Stripe error"""
        mock_create_subscription.side_effect = ValueError("No price found")

        response = self.client.post(
            self.create_subscription_url,
            {
                "subscription_key": "starter_monthly",
                "draw_url": "https://example.com/draw/123",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "No price found")

    @patch("eas.api.stripe.create_subscription")
    def test_create_subscription_unexpected_error(self, mock_create_subscription):
        """Test create_subscription with unexpected error - should raise exception since no error handling"""
        mock_create_subscription.side_effect = Exception("Unexpected error")

        with self.assertRaises(Exception):
            self.client.post(
                self.create_subscription_url,
                {
                    "subscription_key": "starter_monthly",
                    "draw_url": "https://example.com/draw/123",
                },
                content_type="application/json",
            )

    def test_accept_subscription_missing_session_id(self):
        """Test accept_subscription with missing session_id"""
        response = self.client.get(self.accept_subscription_url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "session_id is required")

    @patch("eas.api.stripe.accept_subscription")
    def test_accept_subscription_invalid_session(self, mock_accept_subscription):
        """Test accept_subscription with invalid session"""
        mock_accept_subscription.return_value = False

        response = self.client.get(
            self.accept_subscription_url, {"session_id": "invalid_session"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Subscription not active or invalid")

    @patch("eas.api.stripe.accept_subscription")
    def test_accept_subscription_no_email(self, mock_accept_subscription):
        """Test accept_subscription with valid session but no email"""
        mock_accept_subscription.return_value = ("https://example.com/draw/123", "")

        response = self.client.get(
            self.accept_subscription_url, {"session_id": "cs_test_123"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "No email found in subscription")

    @patch("eas.api.stripe.accept_subscription")
    def test_accept_subscription_success_existing_user(self, mock_accept_subscription):
        """Test successful accept_subscription with existing user"""
        # Create existing user
        existing_user = User.objects.create(
            username="test@example.com", email="test@example.com"
        )
        models.UserProfile.objects.create(user=existing_user)

        mock_accept_subscription.return_value = (
            "https://example.com/draw/123",
            "test@example.com",
        )

        response = self.client.get(
            self.accept_subscription_url, {"session_id": "cs_test_123"}
        )

        # Should redirect to draw URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://example.com/draw/123")

        # User should be logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.email, "test@example.com")

    @patch("eas.api.stripe.accept_subscription")
    def test_accept_subscription_success_new_user(self, mock_accept_subscription):
        """Test successful accept_subscription with new user creation"""
        mock_accept_subscription.return_value = (
            "https://example.com/draw/123",
            "newuser@example.com",
        )

        # Verify user doesn't exist initially
        self.assertFalse(User.objects.filter(email="newuser@example.com").exists())

        response = self.client.get(
            self.accept_subscription_url, {"session_id": "cs_test_123"}
        )

        # Should redirect to draw URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://example.com/draw/123")

        # New user should be created
        new_user = User.objects.get(email="newuser@example.com")
        self.assertEqual(new_user.username, "newuser@example.com")

        # User profile should be created
        self.assertTrue(models.UserProfile.objects.filter(user=new_user).exists())

        # User should be logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.email, "newuser@example.com")

    @patch("eas.api.stripe.accept_subscription")
    def test_accept_subscription_success_no_draw_url(self, mock_accept_subscription):
        """Test successful accept_subscription without draw URL"""
        mock_accept_subscription.return_value = ("", "test@example.com")

        response = self.client.get(
            self.accept_subscription_url, {"session_id": "cs_test_123"}
        )

        # Should return JSON response instead of redirect
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["message"], "Subscription accepted, user logged in"
        )

        # User should be logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.email, "test@example.com")

    @patch("eas.api.stripe.accept_subscription")
    def test_accept_subscription_unexpected_error(self, mock_accept_subscription):
        """Test accept_subscription with unexpected error - should raise exception since no error handling"""
        mock_accept_subscription.side_effect = Exception("Unexpected error")

        with self.assertRaises(Exception):
            self.client.get(self.accept_subscription_url, {"session_id": "cs_test_123"})
