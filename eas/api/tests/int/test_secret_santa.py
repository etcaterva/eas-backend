import datetime as dt
from unittest import mock

import freezegun
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api import models

NOW = dt.datetime.now()


class SecretSantaTest(APILiveServerTestCase):
    def setUp(self):
        self.list_url = reverse("secret-santa-list")
        self.client.default_format = "json"
        self.secret_santa_data = {
            "language": "en",
            "participants": [
                {"name": "First Name", "email": "email@address1.com"},
                {"name": "Second Name", "email": "email@address2.com"},
                {"name": "Third Name", "phone_number": "+34123456789"},
            ],
        }
        boto_patcher = mock.patch("eas.api.amazonsqs.boto3")
        self.sqs = boto_patcher.start().client.return_value
        self.addCleanup(boto_patcher.stop)

    def test_create_secret_santa(self):
        response = self.client.post(self.list_url, self.secret_santa_data)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )
        assert response.json() == {"id": mock.ANY}
        assert self.sqs.send_message.call_count == 1
        assert "email@address1.com" in self.sqs.send_message.call_args[1]["MessageBody"]
        assert "+34123456789" in self.sqs.send_message.call_args[1]["MessageBody"]

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
        self.secret_santa_data = {}
        response = self.client.post(self.list_url, self.secret_santa_data)
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

    def test_missing_target_create(self):
        self.secret_santa_data = {
            "language": "en",
            "participants": [
                {
                    "name": "First Name",
                },
                {
                    "name": "Second Name",
                    "email": "email@address2.com",
                },
                {
                    "name": "Third Name",
                    "email": "email@address2.com",
                },
            ],
        }
        response = self.client.post(self.list_url, self.secret_santa_data)
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )
        assert response.json() == {
            "schema": {
                "participants": {
                    "0": {
                        "non_field_errors": [
                            {"code": "invalid", "message": "phone_or_email_required"}
                        ]
                    }
                }
            }
        }

    def test_fecth_secret_santa_admin(self):
        # Create draw
        response = self.client.post(self.list_url, self.secret_santa_data)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )
        draw_id = response.json()["id"]

        # Fetch admin
        response = self.client.get(
            reverse("secret-santa-admin", kwargs=dict(pk=draw_id))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        result = response.json()
        assert "id" in result
        assert "created_at" in result
        original_participants = {
            p["name"] for p in self.secret_santa_data["participants"]
        }
        returned_participants = {
            p["name"]: p["revealed"] for p in result["participants"]
        }
        assert set(returned_participants) == original_participants
        assert not any(returned_participants.values())
        assert result["participants"][0]["id"]

        # Fetch one result
        draw = models.SecretSanta.objects.get(pk=result["id"])
        draw_result = models.SecretSantaResult.objects.filter(draw=draw).all()[0]
        response = self.client.get(
            reverse("secret-santa-detail", kwargs=dict(pk=draw_result.id))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        fetched_participant = response.json()["source"]

        # Fetch admin
        response = self.client.get(
            reverse("secret-santa-admin", kwargs=dict(pk=draw_id))
        ).json()
        returned_participants = {
            p["name"]: p["revealed"] for p in response["participants"]
        }
        assert len([1 for x in returned_participants.values() if x])
        assert returned_participants[fetched_participant]

    def test_resend_email_success(self):
        draw = models.SecretSanta()
        draw.save()
        result = models.SecretSantaResult(
            source="From name", target="To Name", draw=draw
        )
        result.save()
        assert self.sqs.send_message.call_count == 0

        url = reverse(
            "secret-santa-resend-email",
            kwargs=dict(draw_pk=draw.id, result_pk=result.id),
        )
        with freezegun.freeze_time(NOW + dt.timedelta(days=1)):
            response = self.client.post(
                url, {"language": "en", "email": "mail@mail.com"}
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        assert self.sqs.send_message.call_count == 1

    def test_resend_whatsapp_success(self):
        draw = models.SecretSanta()
        draw.save()
        result = models.SecretSantaResult(
            source="From name", target="To Name", draw=draw
        )
        result.save()
        assert self.sqs.send_message.call_count == 0

        url = reverse(
            "secret-santa-resend-email",
            kwargs=dict(draw_pk=draw.id, result_pk=result.id),
        )
        with freezegun.freeze_time(NOW + dt.timedelta(days=1)):
            response = self.client.post(
                url, {"language": "en", "phone_number": "+34123456789"}
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        assert self.sqs.send_message.call_count == 1

    def test_resend_missing_target(self):
        draw = models.SecretSanta()
        draw.save()
        result = models.SecretSantaResult(
            source="From name", target="To Name", draw=draw
        )
        result.save()
        assert self.sqs.send_message.call_count == 0

        url = reverse(
            "secret-santa-resend-email",
            kwargs=dict(draw_pk=draw.id, result_pk=result.id),
        )
        with freezegun.freeze_time(NOW + dt.timedelta(days=1)):
            response = self.client.post(url, {"language": "en"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert self.sqs.send_message.call_count == 0

    def test_resend_email_unlinked_result_fails(self):
        draw = models.SecretSanta()
        draw.save()
        result = models.SecretSantaResult(
            source="From name", target="To Name", draw=draw
        )
        result.save()
        draw2 = models.SecretSanta()
        draw2.save()
        result2 = models.SecretSantaResult(
            source="From name", target="To Name", draw=draw2
        )
        result2.save()

        url = reverse(
            "secret-santa-resend-email",
            kwargs=dict(draw_pk=draw2.id, result_pk=result.id),
        )
        response = self.client.post(url, {"language": "en", "email": "mail@mail.com"})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

        url = reverse(
            "secret-santa-resend-email",
            kwargs=dict(draw_pk=draw.id, result_pk=result2.id),
        )
        response = self.client.post(url, {"language": "en", "email": "mail@mail.com"})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )
        self.assertEqual(response.json()["general"][0]["code"], "invalid")

    def test_resend_email_revealed_result_fails(self):
        draw = models.SecretSanta()
        draw.save()
        result = models.SecretSantaResult(
            source="From name", target="To Name", draw=draw
        )
        result.save()

        response = self.client.get(
            reverse("secret-santa-detail", kwargs=dict(pk=result.id))
        )

        url = reverse(
            "secret-santa-resend-email",
            kwargs=dict(draw_pk=draw.id, result_pk=result.id),
        )
        response = self.client.post(url, {"language": "en", "email": "mail@mail.com"})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )
        self.assertEqual(response.json()["general"][0]["code"], "revealed")

    def test_resend_email_too_recent_fails(self):
        draw = models.SecretSanta()
        draw.save()
        result = models.SecretSantaResult(
            source="From name", target="To Name", draw=draw
        )
        result.save()

        url = reverse(
            "secret-santa-resend-email",
            kwargs=dict(draw_pk=draw.id, result_pk=result.id),
        )
        response = self.client.post(url, {"language": "en", "email": "mail@mail.com"})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )
        self.assertEqual(response.json()["general"][0]["code"], "too-early")

    def test_resend_email_invalidates_previous_result(self):
        new_email_data = {"language": "en", "email": "mail@mail.com"}
        draw = models.SecretSanta()
        draw.save()
        result = models.SecretSantaResult(
            source="From name", target="To Name", draw=draw
        )
        result.save()
        assert self.sqs.send_message.call_count == 0

        url = reverse(
            "secret-santa-resend-email",
            kwargs=dict(draw_pk=draw.id, result_pk=result.id),
        )
        with freezegun.freeze_time(NOW + dt.timedelta(days=1)):
            response = self.client.post(url, new_email_data)
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
            assert self.sqs.send_message.call_count == 1
            new_result_id = response.json()["new_result"]

            # Send email on same result is invalid
            response = self.client.post(url, new_email_data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.json()["general"][0]["code"], "invalid")

            # Send email on new result is too early
            url = reverse(
                "secret-santa-resend-email",
                kwargs=dict(draw_pk=draw.id, result_pk=new_result_id),
            )
            response = self.client.post(url, new_email_data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.json()["general"][0]["code"], "too-early")

            # OK to fetch new result
            response = self.client.get(
                reverse("secret-santa-detail", kwargs=dict(pk=new_result_id))
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

            # Fails to fetch old result
            response = self.client.get(
                reverse("secret-santa-detail", kwargs=dict(pk=result.id))
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
