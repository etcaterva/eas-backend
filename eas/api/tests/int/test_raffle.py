from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api.models import Raffle
from .common import DrawAPITestMixin, StrDatetimeMatcher
from ..factories import RaffleFactory


class TestRaffle(DrawAPITestMixin, APILiveServerTestCase):
    maxDiff = None
    base_url = 'raffle'
    Model = Raffle
    Factory = RaffleFactory

    def as_expected_result(self, draw, write_access=False):
        return {
            **super().as_expected_result(draw, write_access),
            'participants': [dict(
                id=p.id,
                created_at=StrDatetimeMatcher(p.created_at),
                name=p.name,
                facebook_id=p.facebook_id,
            ) for p in draw.participants],
            'prizes': [dict(
                id=p.id,
                created_at=StrDatetimeMatcher(p.created_at),
                name=p.name,
                url=p.url,
            ) for p in draw.prizes],
        }

    def test_creation_invalid(self):
        url = reverse(f'{self.base_url}-list')
        data = self.Factory.dict(prizes=[])
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         response.content)

    def test_duplicated_prize(self):
        draw = self.Factory(prizes=[{"name": "cupcake"}, {"name": "cupcake"}])
        url = reverse(f'{self.base_url}-toss',
                      kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        result1, result2 = response.json()["value"]
        self.assertEqual(result1["prize"]["name"], "cupcake")
        self.assertEqual(result2["prize"]["name"], "cupcake")
        self.assertNotEqual(result1["prize"]["id"], result2["prize"]["id"])

    def test_insuficient_participants(self):
        draw = self.Factory(participants=[])
        url = reverse(f'{self.base_url}-toss',
                      kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         response.content)

    def test_add_participants(self):
        draw = self.Factory(participants=[])
        assert not draw.participants

        url = reverse(f'{self.base_url}-participants',
                      kwargs=dict(pk=draw.id))
        response = self.client.post(url, {
            "name": "paco",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         response.content)
        draw = self.get_draw(draw.id)
        assert len(draw.participants) == 1
        assert draw.participants[0].name == "paco"

        response = self.client.post(url, {
            "name": "ramon",
            "facebook_id": "this_is_an_id"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         response.content)
        draw = self.get_draw(draw.id)
        assert len(draw.participants) == 2
        assert draw.participants[1].name == "ramon"
        assert draw.participants[1].facebook_id == "this_is_an_id"
