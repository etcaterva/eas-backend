from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api.models import Lottery
from .common import DrawAPITestMixin
from ..factories import LotteryFactory


class TestLottery(DrawAPITestMixin, APILiveServerTestCase):
    maxDiff = None
    base_url = 'lottery'
    Model = Lottery
    Factory = LotteryFactory

    def _transform_draw(self, draw, write_access):
        return {
            **super()._transform_draw(draw, write_access),
            'participants': [dict(
                id=p.id,
                created_at=p.created_at,
                name=p.name,
                facebook_id=p.facebook_id,
            ) for p in draw.participants],
        }

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
