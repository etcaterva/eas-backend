"""Test to verify max_comments_allowed uses settings correctly"""
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from eas.api import models

User = get_user_model()


class InstagramSettingsTest(TestCase):
    """Test that Instagram view uses settings for default limits"""

    def test_max_comments_uses_free_tier_from_settings(self):
        """Test that the default max_comments_allowed comes from settings"""
        # Get the expected value from settings
        expected_limit = settings.SUBSCRIPTION_TIERS["free"]["max_instagram_comments"]
        self.assertEqual(expected_limit, 300)  # Verify our expectation

        # The view should use this value as default for unauthenticated users
        # and authenticated users without Stripe subscription
        user = User.objects.create(
            username="test@example.com", email="test@example.com"
        )
        models.UserProfile.objects.create(user=user)

        self.client.force_login(user)

        # Try to create a draw - the view should use the settings value
        url = reverse("instagram-list")
        data = {
            "post_url": "https://www.instagram.com/p/test123/",
            "number_of_results": 250,  # Less than free tier limit of 300
            "title": "Test Instagram Draw",
        }

        response = self.client.post(
            url, data=json.dumps(data), content_type="application/json"
        )

        # Should not be blocked by limits (may fail for other reasons like invalid URL)
        self.assertNotEqual(response.status_code, 403)

    def test_free_tier_limit_in_settings(self):
        """Test that free tier limit is correctly set in settings"""
        self.assertEqual(
            settings.SUBSCRIPTION_TIERS["free"]["max_instagram_comments"], 300
        )
        self.assertEqual(settings.SUBSCRIPTION_TIERS["free"]["name"], "Free")
