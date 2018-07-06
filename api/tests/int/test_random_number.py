import dateutil.parser
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from api.models import RandomNumber
from ..factories import RandomNumberFactory


class StrDatetimeMatcher:
    def __init__(self, expected):
        self.expected = expected

    def __eq__(self, other):
        return self.expected == dateutil.parser.parse(other)

    def __repr__(self):  # pragma: no cover
        return f"{self.__class__.__name__}({self.expected})"


class TestRandomNumber(APILiveServerTestCase):
    maxDiff = None

    def setUp(self):
        self.draws = RandomNumberFactory.create_batch(size=50)
        self.draw = RandomNumberFactory()
        self.client.default_format = 'json'

    @staticmethod
    def get_draw(id_):
        return RandomNumber.objects.get(id=id_)

    @staticmethod
    def as_expected_result(draw, write_access=False):
        result = {
            'id': draw.id,
            'created_at': StrDatetimeMatcher(draw.created_at),
            'updated_at': StrDatetimeMatcher(draw.updated_at),
            'title': draw.title,
            'description': draw.description,
            'range_min': draw.range_min,
            'range_max': draw.range_max,
            'metadata': [],
            'results': [dict(
                created_at=StrDatetimeMatcher(r.created_at),
                value=r.value
            ) for r in draw.results.order_by("-created_at")],
        }

        if write_access:
            result["private_id"] = draw.private_id

        return result

    def test_creation(self):
        url = reverse('random_number-list')
        data = RandomNumberFactory.dict()
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        db_draw = self.get_draw(response.data["id"])
        expected_result = self.as_expected_result(db_draw, write_access=True)
        self.assertEqual(response.data.keys(), expected_result.keys())
        self.assertEqual(response.data, expected_result)

    def test_creation_invalid(self):
        url = reverse('random_number-list')
        data = RandomNumberFactory.dict(range_min=5, range_max=4)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve(self):
        self.draw.toss()
        url = reverse('random_number-detail', kwargs=dict(pk=self.draw.id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_result = self.as_expected_result(self.draw)
        self.assertEqual(response.data.keys(), expected_result.keys())
        self.assertEqual(response.data, expected_result)

    def test_retrieve_with_private_id(self):
        self.draw.toss()
        url = reverse('random_number-detail',
                      kwargs=dict(pk=self.draw.private_id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_result = self.as_expected_result(self.draw, write_access=True)
        self.assertEqual(response.data.keys(), expected_result.keys())
        self.assertEqual(response.data, expected_result)

    def test_toss(self):
        url = reverse('random_number-toss',
                      kwargs=dict(pk=str(self.draw.private_id)))
        toss_response = self.client.post(url)

        self.assertEqual(toss_response.status_code, status.HTTP_200_OK)
        self.assertEqual(toss_response.data["value"],
                         self.draw.results.first().value)

        url = reverse('random_number-detail', kwargs=dict(pk=self.draw.id))
        response = self.client.get(url)
        expected_result = self.as_expected_result(self.draw)
        self.assertEqual(response.data.keys(), expected_result.keys())
        self.assertEqual(1, len(response.data["results"]))
        self.assertEqual(response.data, expected_result)

    def test_create_and_retrieve_metadata(self):
        url = reverse('random_number-list')
        data = RandomNumberFactory.dict()
        data["metadata"] = [
            dict(client="web", key="chat_enabled", value="false"),
            dict(client="web", key="premium_customer", value="true"),
        ]
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        chat_enabled_data, = [i for i in response.data["metadata"]
                              if i["key"] == "chat_enabled"]
        self.assertEqual(chat_enabled_data, dict(
            client="web", key="chat_enabled", value="false"
        ))
