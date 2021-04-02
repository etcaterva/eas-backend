import datetime as dt
import time

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api.models import Raffle

from ..factories import RaffleFactory
from .common import DrawAPITestMixin


class TestRaffle(DrawAPITestMixin, APILiveServerTestCase):
    maxDiff = None
    base_url = "raffle"
    Model = Raffle
    Factory = RaffleFactory

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
            "prizes": [
                dict(
                    id=p.id,
                    created_at=p.created_at,
                    name=p.name,
                    url=p.url,
                )
                for p in draw.prizes
            ],
        }

    def test_creation_invalid(self):
        response = self.create(prizes=[])
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def test_duplicated_prize(self):
        draw = self.Factory(prizes=[{"name": "cupcake"}, {"name": "cupcake"}])
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        result1, result2 = response.json()["value"]
        self.assertEqual(result1["prize"]["name"], "cupcake")
        self.assertEqual(result2["prize"]["name"], "cupcake")
        self.assertNotEqual(result1["prize"]["id"], result2["prize"]["id"])

    def test_0_participants_fail(self):
        draw = self.Factory(participants=[])
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def test_insuficient_participants(self):
        draw = self.Factory(
            participants=[{"name": "one"}],
            prizes=[{"name": "cupcake"}, {"name": "cupcake"}],
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        result1, result2 = response.json()["value"]
        self.assertEqual(result1["prize"]["name"], "cupcake")
        self.assertEqual(result2["prize"]["name"], "cupcake")
        self.assertEqual(result1["participant"]["name"], "one")
        self.assertEqual(result2["participant"]["name"], "one")

    def test_insuficient_participants_ignored_on_schedule_toss(self):
        draw = self.Factory(participants=[])
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        now = dt.datetime.now(dt.timezone.utc)
        response = self.client.post(
            url,
            {
                "schedule_date": now - dt.timedelta(hours=5),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        draw = self.get_draw(draw.id)
        self.assertIsNone(draw.results.values()[0]["value"])

        url = reverse(f"{self.base_url}-detail", kwargs=dict(pk=draw.id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

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

    def test_add_participants_twice_ignores_twice_fb_id(self):
        draw = self.Factory(participants=[])
        assert not draw.participants

        url = reverse(f"{self.base_url}-participants", kwargs=dict(pk=draw.id))
        self.client.post(
            url,
            {
                "name": "paco",
            },
        )
        self.client.post(url, {"name": "ramon", "facebook_id": "this_is_an_id"})
        self.client.post(
            url,
            {
                "name": "paco",
            },
        )
        assert len(self.get_draw(draw.id).participants) == 3

        self.client.post(url, {"name": "ramon", "facebook_id": "this_is_an_id"})

        draw = self.get_draw(draw.id)
        assert len(draw.participants) == 3
        assert draw.participants[0].name == "paco"
        assert draw.participants[1].name == "ramon"
        assert draw.participants[1].facebook_id == "this_is_an_id"
        assert draw.participants[2].name == "paco"

    def test_add_participants_increments_last_updated(self):
        draw = self.Factory(participants=[])
        initial_last_updated = draw.updated_at

        time.sleep(0.1)
        url = reverse(f"{self.base_url}-participants", kwargs=dict(pk=draw.id))
        self.client.post(url, {"name": "paco"})

        draw = self.get_draw(draw.id)
        assert draw.updated_at > initial_last_updated

    def test_toss_increments_last_updated(self):
        draw = self.Factory()
        initial_last_updated = draw.updated_at

        time.sleep(0.1)
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        self.client.post(url, {})

        draw = self.get_draw(draw.id)
        assert draw.updated_at > initial_last_updated
