from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api.models import Letter

from ..factories import LetterFactory
from .common import DrawAPITestMixin


class TestLetter(DrawAPITestMixin, APILiveServerTestCase):
    maxDiff = None
    base_url = "letter"
    Model = Letter
    Factory = LetterFactory

    def as_expected_result(self, draw, write_access=False):
        return {
            **super().as_expected_result(draw, write_access),
            "number_of_results": draw.number_of_results,
            "allow_repeated_results": draw.allow_repeated_results,
        }

    def test_creation_invalid(self):
        response = self.create(number_of_results=27)
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def test_creation_valid(self):
        response = self.create(number_of_results=27, allow_repeated_results=True)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )
