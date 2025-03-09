import os
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api import models

from .. import factories


class RevolutTestEnd2End(APILiveServerTestCase):
    def setUp(self):
        self.client.default_format = "json"
        self.draw_id = factories.RaffleFactory().id
        self.create_url = reverse("revolut-create")
        self.accept_url = reverse("revolut-accept", kwargs={"draw_id": self.draw_id})

    @pytest.mark.skipif(
        "EAS_REVOLUT_SECRET" not in os.environ, reason="EAS_REVOLUT_SECRET unset"
    )
    def test_create_payment_end_to_end(self):
        response = self.client.post(
            self.create_url,
            {
                "options": ["CERTIFIED"],
                "draw_id": self.draw_id,
                "draw_url": "https://test.com",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        assert response.json()["redirect_url"]
        response = self.client.get(self.accept_url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND, response.content)


class RevolutTestPublicDraw(APILiveServerTestCase):
    def setUp(self):
        self.client.default_format = "json"
        self.draw_id = factories.RaffleFactory().id
        self.create_url = reverse("revolut-create")
        self.accept_url = reverse("revolut-accept", kwargs={"draw_id": self.draw_id})

    @property
    def draw(self):
        return models.Raffle.objects.get(id=self.draw_id)

    @mock.patch("eas.api.revolut.accept_payment")
    @mock.patch("eas.api.revolut.create_payment")
    def test_full_payment_public_draw(self, create_payment, _):
        assert self.draw.payments == []
        url = reverse("raffle-detail", kwargs=dict(pk=self.draw.id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        assert response.json()["payments"] == []

        create_payment.return_value = "revolut-id", "fake-url"
        response = self.client.post(
            self.create_url,
            {
                "options": ["CERTIFIED", "ADFREE", "SUPPORT"],
                "draw_id": self.draw.id,
                "draw_url": "http://test.com",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        assert response.json()["redirect_url"] == "fake-url"

        response = self.client.get(
            self.accept_url, {"token": "revolut-id", "PayerID": "payer-id"}
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND, response.content)
        assert response.url == "http://test.com"
        assert self.draw.payments == ["CERTIFIED", "ADFREE", "SUPPORT"]

        url = reverse("raffle-detail", kwargs=dict(pk=self.draw.id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        assert response.json()["payments"] == ["CERTIFIED", "ADFREE", "SUPPORT"]


class RevolutTestSecretSanta(APILiveServerTestCase):
    def setUp(self):
        self.client.default_format = "json"
        self.draw = models.SecretSanta()
        self.draw.save()
        for i in range(3):
            result = models.SecretSantaResult(
                draw=self.draw, source=f"Person {i}", target=f"Person {2-i}"
            )
            result.save()
        self.create_url = reverse("revolut-create")
        self.accept_url = reverse("revolut-accept", kwargs={"draw_id": self.draw.id})

    @mock.patch("eas.api.revolut.accept_payment")
    @mock.patch("eas.api.revolut.create_payment")
    def test_full_payment_secret_santa(self, create_payment, _):
        assert self.draw.payments == []
        url = reverse("secret-santa-admin", kwargs=dict(pk=self.draw.id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        assert response.json()["payments"] == []

        create_payment.return_value = "revolut-id", "fake-url"
        response = self.client.post(
            self.create_url,
            {
                "options": ["CERTIFIED", "ADFREE", "SUPPORT"],
                "draw_id": self.draw.id,
                "draw_url": "http://test.com",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        assert response.json()["redirect_url"] == "fake-url"

        response = self.client.get(
            self.accept_url, {"token": "revolut-id", "PayerID": "payer-id"}
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND, response.content)
        assert response.url == "http://test.com"
        assert self.draw.payments == ["CERTIFIED", "ADFREE", "SUPPORT"]

        url = reverse("secret-santa-admin", kwargs=dict(pk=self.draw.id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        assert response.json()["payments"] == ["CERTIFIED", "ADFREE", "SUPPORT"]
