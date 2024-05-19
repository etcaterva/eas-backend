from unittest.mock import ANY

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

    def test_success_2part_valid_result(self):
        draw = self.Factory(participants=[dict(name=name) for name in ["1", "2"]])
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        result = self.client.post(url, {}).json()["value"]
        assert len(result) == 1
        assert result == [
            {
                "id": ANY,
                "next_match_id": None,
                "participant_1": {
                    "facebook_id": None,
                    "name": ANY,
                    "id": ANY,
                },
                "participant_2": {
                    "facebook_id": None,
                    "name": ANY,
                    "id": ANY,
                },
                "score": None,
                "winner_id": None,
            }
        ]
        assert result[0]["participant_1"]["name"] in ["1", "2"]
        assert result[0]["participant_2"]["name"] in ["1", "2"]
        assert result[0]["participant_1"]["name"] != result[0]["participant_2"]["name"]

    def test_success_4_people_has_empty_match(self):
        draw = self.Factory(
            participants=[dict(name=name) for name in ["1", "2", "3", "4"]]
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        result = self.client.post(url, {}).json()["value"]
        assert len(result) == 3
        assert result[0]["next_match_id"] == result[2]["id"]
        assert result[2] == {
            "id": 2,
            "next_match_id": None,
            "participant_1": None,
            "participant_2": None,
            "score": None,
            "winner_id": None,
        }

    def test_success_5_people_add_phamtom_matches(self):
        draw = self.Factory(
            participants=[dict(name=name) for name in ["1", "2", "3", "4", "5"]]
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        result = self.client.post(url, {}).json()["value"]
        assert len(result) == 7
        empty_match = {
            "id": ANY,
            "next_match_id": ANY,
            "participant_1": None,
            "participant_2": None,
            "score": None,
            "winner_id": None,
        }
        assert result[6] == empty_match

        assert result[0]["participant_1"]
        assert result[0]["participant_2"]
        assert result[0]["next_match_id"] == result[4]["id"]

        assert result[1]["participant_1"]
        assert result[1]["participant_2"] is None
        assert result[1]["next_match_id"] == result[4]["id"]

        assert result[2]["participant_1"]
        assert result[2]["participant_2"] is None
        assert result[2]["next_match_id"] == result[5]["id"]

        assert result[3]["participant_1"]
        assert result[3]["participant_2"] is None
        assert result[3]["next_match_id"] == result[5]["id"]

        assert result[4]["participant_1"]["id"] == result[1]["winner_id"]
        assert result[4]["participant_2"] is None
        assert result[4]["next_match_id"] == result[6]["id"]

        assert result[5]["participant_1"]["id"] == result[2]["winner_id"]
        assert result[5]["participant_2"]["id"] == result[3]["winner_id"]
        assert result[5]["next_match_id"] == result[6]["id"]
