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

    def as_expected_result(self, draw, write_access=False):
        return {
            **super().as_expected_result(draw, write_access),
            'range_min': draw.range_min,
            'range_max': draw.range_max,
            'number_of_results': draw.number_of_results,
            'allow_repeated_results': draw.allow_repeated_results
        }

    def test_creation_invalid(self):
        url = reverse(f'{self.base_url}-list')
        data = self.Factory.dict(range_min=5, range_max=4)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         response.content)

    def test_creation_miss_optional_fields(self):
        url = reverse(f'{self.base_url}-list')
        data = self.Factory.dict(range_min=1, range_max=4)
        data.pop("allow_repeated_results")
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


    def test_creation_invalid_repeated(self):
        url = reverse(f'{self.base_url}-list')
        data = self.Factory.dict(range_min=1, range_max=10,
                                 number_of_results=10)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         response.content)
