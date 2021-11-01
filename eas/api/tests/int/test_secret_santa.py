from unittest import mock

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api import models


class SecretSantaTest(APILiveServerTestCase):
    def setUp(self):
        self.list_url = reverse("secret-santa-list")
        self.client.default_format = "json"
        self.secret_santa_data = {
            "language": "en",
            "participants": [
                {"name": "First Name", "email": "email@address1.com"},
                {"name": "Second Name", "email": "email@address2.com"},
                {"name": "Third Name", "email": "email@address2.com"},
            ],
        }
        boto_patcher = mock.patch("eas.api.amazonsqs.boto3")
        boto_patcher.start()
        self.addCleanup(boto_patcher.stop)

    def test_create_secret_santa(self):
        response = self.client.post(self.list_url, self.secret_santa_data)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

    def test_create_with_exclusions(self):
        self.secret_santa_data = {
            "language": "en",
            "participants": [
                {
                    "name": "First Name",
                    "email": "email@address1.com",
                    "exclusions": ["Third Name"],
                },
                {
                    "name": "Second Name",
                    "email": "email@address2.com",
                    "exclusions": ["First Name"],
                },
                {
                    "name": "Third Name",
                    "email": "email@address2.com",
                    "exclusions": ["Second Name"],
                },
            ],
        }
        response = self.client.post(self.list_url, self.secret_santa_data)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )
        results = list(models.SecretSantaResult.objects.all())
        assert len(results) == 3
        print(results)
        assert any(
            r.source == "First Name" and r.target == "Second Name" for r in results
        )
        assert any(
            r.source == "Second Name" and r.target == "Third Name" for r in results
        )
        assert any(
            r.source == "Third Name" and r.target == "First Name" for r in results
        )

    def test_create_impossible(self):
        self.secret_santa_data = {
            "language": "en",
            "participants": [
                {
                    "name": "First Name",
                    "email": "email@address1.com",
                    "exclusions": ["Third Name"],
                },
                {
                    "name": "Second Name",
                    "email": "email@address2.com",
                    "exclusions": ["Third Name"],
                },
                {
                    "name": "Third Name",
                    "email": "email@address2.com",
                    "exclusions": ["Second Name"],
                },
            ],
        }
        response = self.client.post(self.list_url, self.secret_santa_data)
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )
        assert response.json() == {
            "general": [{"message": "Unable to match participants", "code": "invalid"}]
        }

    def test_retrieve(self):
        result = models.SecretSantaResult(source="From name", target="To Name")
        result.save()
        url = reverse("secret-santa-detail", kwargs=dict(pk=result.id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data, {"source": "From name", "target": "To Name"})

    def test_missing_fields(self):
        secret_santa_data = {}
        response = self.client.post(self.list_url, secret_santa_data)
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )
        assert response.json() == {
            "schema": {
                "participants": [
                    {"message": "This field is required.", "code": "required"}
                ],
                "language": [
                    {"message": "This field is required.", "code": "required"}
                ],
            }
        }
