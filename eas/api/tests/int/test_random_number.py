from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api.models import RandomNumber
from .common import DrawAPITestMixin
from ..factories import RandomNumberFactory


class TestRandomNumber(DrawAPITestMixin, APILiveServerTestCase):
    maxDiff = None
    base_url = 'random_number'
    Model = RandomNumber
    Factory = RandomNumberFactory

    def test_creation_invalid(self):
        url = reverse(f'{self.base_url}-list')
        data = self.Factory.dict(range_min=5, range_max=4)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         response.content)

    def as_expected_result(self, draw, write_access=False):
        return {
            **super().as_expected_result(draw, write_access),
            'range_min': draw.range_min,
            'range_max': draw.range_max,
            'number_of_results': draw.number_of_results,
        }
