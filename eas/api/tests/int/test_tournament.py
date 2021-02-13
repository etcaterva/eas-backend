from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api.models import Tournament

from ..factories import TournamentFactory
from .common import DrawAPITestMixin


class TestTournament(DrawAPITestMixin, APILiveServerTestCase):
    maxDiff = None
    base_url = "tournament"
    Model = Tournament
    Factory = TournamentFactory

    def _transform_draw(self, draw, write_access):
        return {
            **super()._transform_draw(draw, write_access),
            "participants": [
                dict(
                    id=p.id,
                    created_at=p.created_at,
                    name=p.name,
                    facebook_id=p.facebook_id,
                )
                for p in draw.participants
            ],
        }

    def test_add_participants(self):
        draw = self.Factory(participants=[])
        assert not draw.participants

        url = reverse(f"{self.base_url}-participants", kwargs=dict(pk=draw.id))
        response = self.client.post(
            url,
            {
                "name": "paco",
            },
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )
        draw = self.get_draw(draw.id)
        assert len(draw.participants) == 1
        assert draw.participants[0].name == "paco"

        response = self.client.post(
            url, {"name": "ramon", "facebook_id": "this_is_an_id"}
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )
        draw = self.get_draw(draw.id)
        assert len(draw.participants) == 2
        assert draw.participants[1].name == "ramon"
        assert draw.participants[1].facebook_id == "this_is_an_id"
