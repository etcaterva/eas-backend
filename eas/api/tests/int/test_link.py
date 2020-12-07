from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api.models import Link

from ..factories import LinkFactory
from .common import DrawAPITestMixin


class TestLink(DrawAPITestMixin, APILiveServerTestCase):
    maxDiff = None
    base_url = "link"
    Model = Link
    Factory = LinkFactory

    def as_expected_result(self, draw, write_access=False):
        return {
            **super().as_expected_result(draw, write_access),
            "items_set1": draw.items_set1,
            "items_set2": draw.items_set2,
        }

    def test_creation_invalid(self):
        response = self.create(items_set1=[])
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def test_creation_invalid2(self):
        response = self.create(items_set2=[])
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def test_duplicated_item(self):
        draw = self.Factory(items_set1=["dup", "dup"])
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        result1, result2 = response.json()["value"]
        self.assertEqual(result1["element1"], "dup")
        self.assertEqual(result2["element1"], "dup")
        self.assertNotEqual(result1["element2"], result2["element2"])
