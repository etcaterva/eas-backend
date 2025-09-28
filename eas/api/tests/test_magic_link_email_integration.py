"""Integration tests for magic link email functionality"""
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from eas.api import models

User = get_user_model()


class MagicLinkEmailIntegrationTest(TestCase):
    """Test complete magic link email flow"""

    def setUp(self):
        self.magic_link_url = reverse("request-magic-link")
        self.test_email = "test@example.com"
        self.return_url = "https://example.com/success"

    @patch("eas.api.email.boto3.client")
    def test_magic_link_request_sends_email(self, mock_boto_client):
        """Test that requesting magic link sends email via SES"""
        # Mock SES client response
        mock_ses = Mock()
        mock_ses.send_email.return_value = {"MessageId": "test-message-id"}
        mock_boto_client.return_value = mock_ses

        # Request magic link
        response = self.client.post(
            self.magic_link_url,
            {"email": self.test_email, "return_url": self.return_url},
            content_type="application/json",
        )

        # Verify success response
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["message"], "Magic link sent successfully")

        # Verify user was created
        user = User.objects.get(email=self.test_email)
        self.assertEqual(user.username, self.test_email)

        # Verify token was created with return_url
        token = models.LoginToken.objects.get(user=user)
        self.assertEqual(token.return_url, self.return_url)

        # Verify SES was called correctly
        mock_ses.send_email.assert_called_once()
        _, kwargs = mock_ses.send_email.call_args

        # Check email parameters
        self.assertEqual(
            kwargs["Source"], "Echalo A Suerte <no-reply@echaloasuerte.com>"
        )
        self.assertEqual(kwargs["Destination"]["ToAddresses"], [self.test_email])

        # Check that token is in the email content
        html_body = kwargs["Message"]["Body"]["Html"]["Data"]
        text_body = kwargs["Message"]["Body"]["Text"]["Data"]
        self.assertIn(token.token, html_body)
        self.assertIn(token.token, text_body)

    @patch("eas.api.email.boto3.client")
    def test_magic_link_request_email_failure(self, mock_boto_client):
        """Test handling of email sending failure"""
        # Mock SES client to fail
        mock_ses = Mock()
        mock_ses.send_email.side_effect = Exception("SES error")
        mock_boto_client.return_value = mock_ses

        # Request magic link
        response = self.client.post(
            self.magic_link_url,
            {"email": self.test_email, "return_url": self.return_url},
            content_type="application/json",
        )

        # Verify error response
        self.assertEqual(response.status_code, 500)
        response_data = response.json()
        self.assertEqual(response_data["error"], "Failed to send magic link")

        # Verify user and token were still created (just email failed)
        user = User.objects.get(email=self.test_email)
        self.assertEqual(user.username, self.test_email)
        token = models.LoginToken.objects.get(user=user)
        self.assertEqual(token.return_url, self.return_url)

    @patch("eas.api.email.boto3.client")
    def test_existing_user_magic_link(self, mock_boto_client):
        """Test magic link for existing user"""
        # Mock SES client response
        mock_ses = Mock()
        mock_ses.send_email.return_value = {"MessageId": "test-message-id"}
        mock_boto_client.return_value = mock_ses

        # Create existing user
        existing_user = User.objects.create(
            username=self.test_email, email=self.test_email
        )

        # Request magic link
        response = self.client.post(
            self.magic_link_url,
            {"email": self.test_email, "return_url": self.return_url},
            content_type="application/json",
        )

        # Verify success
        self.assertEqual(response.status_code, 200)

        # Should not create duplicate user
        self.assertEqual(User.objects.filter(email=self.test_email).count(), 1)

        # Check token was created for existing user
        token = models.LoginToken.objects.get(user=existing_user)
        self.assertEqual(token.return_url, self.return_url)

        # Verify email was sent
        mock_ses.send_email.assert_called_once()
