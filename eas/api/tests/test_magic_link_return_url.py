"""Test magic link with return URL functionality"""
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from eas.api import models

User = get_user_model()


class MagicLinkReturnUrlTest(TestCase):
    """Test magic link functionality with return URL"""

    def setUp(self):
        """Set up test data"""
        self.magic_link_url = reverse("request-magic-link")
        self.verify_url = reverse("verify-magic-link")
        self.test_email = "test@example.com"
        self.return_url = "https://example.com/success"

    def test_request_magic_link_without_return_url(self):
        """Test requesting magic link without return URL should fail"""
        response = self.client.post(
            self.magic_link_url,
            {"email": self.test_email},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data["error"], "Return URL is required")

        # Check no user was created
        self.assertFalse(User.objects.filter(email=self.test_email).exists())

    @patch("eas.api.email.boto3.client")
    def test_request_magic_link_with_return_url(self, mock_boto_client):
        """Test requesting magic link with return URL"""
        # Mock SES client
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {"MessageId": "test-message-id"}
        mock_boto_client.return_value = mock_ses

        response = self.client.post(
            self.magic_link_url,
            {"email": self.test_email, "return_url": self.return_url},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        # Check user was created
        user = User.objects.get(email=self.test_email)
        self.assertEqual(user.username, self.test_email)

        # Check token was created with return_url
        token = models.LoginToken.objects.get(user=user)
        self.assertEqual(token.return_url, self.return_url)

    def test_verify_magic_link_with_return_url(self):
        """Test verifying magic link and redirecting to return URL"""
        # Create user and token with return URL
        user = User.objects.create(username=self.test_email, email=self.test_email)
        token = models.LoginToken.create_for_user(user, return_url=self.return_url)

        response = self.client.get(self.verify_url, {"token": token.token})

        # Should redirect to return_url
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.return_url)

        # User should be logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.email, self.test_email)

        # Token should be deleted
        self.assertFalse(models.LoginToken.objects.filter(token=token.token).exists())

    def test_verify_invalid_token(self):
        """Test verifying with invalid token"""
        response = self.client.get(self.verify_url, {"token": "invalid-token"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Invalid or expired token")

    def test_request_magic_link_missing_email(self):
        """Test requesting magic link without email"""
        response = self.client.post(
            self.magic_link_url,
            {"return_url": self.return_url},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Email is required")

    @patch("eas.api.email.boto3.client")
    def test_existing_user_with_return_url(self, mock_boto_client):
        """Test requesting magic link for existing user with return URL"""
        # Mock SES client
        mock_ses = MagicMock()
        mock_ses.send_email.return_value = {"MessageId": "test-message-id"}
        mock_boto_client.return_value = mock_ses

        # Create existing user
        existing_user = User.objects.create(
            username=self.test_email, email=self.test_email
        )

        response = self.client.post(
            self.magic_link_url,
            {"email": self.test_email, "return_url": self.return_url},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        # Should not create duplicate user
        self.assertEqual(User.objects.filter(email=self.test_email).count(), 1)

        # Check token was created with return_url
        token = models.LoginToken.objects.get(user=existing_user)
        self.assertEqual(token.return_url, self.return_url)
