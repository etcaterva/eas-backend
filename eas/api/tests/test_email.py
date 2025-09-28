"""Tests for email functionality"""
from unittest.mock import Mock, patch

from django.test import TestCase

from eas.api import email


class EmailServiceTest(TestCase):
    """Test email sending functionality"""

    @patch("eas.api.email.boto3.client")
    def test_send_magic_link_success(self, mock_boto_client):
        """Test successful magic link email sending"""
        # Mock SES client response
        mock_ses = Mock()
        mock_ses.send_email.return_value = {"MessageId": "test-message-id"}
        mock_boto_client.return_value = mock_ses

        # Test email sending
        test_email = "test@example.com"
        test_magic_link = "https://example.com/verify?token=abc123"

        result = email.send_magic_link(test_email, test_magic_link)

        # Verify success
        self.assertTrue(result)

        # Verify SES client was created correctly
        mock_boto_client.assert_called_once_with(
            "ses",
            region_name="us-east-2",
            aws_access_key_id="AKIAQ337QRVCGGGT4UH6",
            aws_secret_access_key=None,  # Will be None in test environment
        )

        # Verify email was sent with correct parameters
        mock_ses.send_email.assert_called_once()
        _, kwargs = mock_ses.send_email.call_args

        # Check email parameters
        self.assertEqual(
            kwargs["Source"], "Echalo A Suerte <no-reply@echaloasuerte.com>"
        )
        self.assertEqual(kwargs["Destination"]["ToAddresses"], [test_email])
        self.assertEqual(
            kwargs["Message"]["Subject"]["Data"], "Tu enlace mágico - Échalo A Suerte"
        )

        # Check that magic link is in both HTML and text body
        html_body = kwargs["Message"]["Body"]["Html"]["Data"]
        text_body = kwargs["Message"]["Body"]["Text"]["Data"]
        self.assertIn(test_magic_link, html_body)
        self.assertIn(test_magic_link, text_body)

    @patch("eas.api.email.boto3.client")
    def test_send_magic_link_failure(self, mock_boto_client):
        """Test magic link email sending failure"""
        # Mock SES client to raise exception
        mock_ses = Mock()
        mock_ses.send_email.side_effect = Exception("SES error")
        mock_boto_client.return_value = mock_ses

        # Test email sending
        test_email = "test@example.com"
        test_magic_link = "https://example.com/verify?token=abc123"

        result = email.send_magic_link(test_email, test_magic_link)

        # Verify failure
        self.assertFalse(result)

        # Verify SES send_email was attempted
        mock_ses.send_email.assert_called_once()

    def test_sender_configuration(self):
        """Test that sender is configured correctly"""
        self.assertEqual(email.SENDER, "Echalo A Suerte <no-reply@echaloasuerte.com>")
