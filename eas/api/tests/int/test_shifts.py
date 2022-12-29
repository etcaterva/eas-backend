import datetime as dt
from unittest.mock import ANY

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api.models import Shifts

from ..factories import ShiftsFactory
from .common import DrawAPITestMixin

NOW = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=365)
NOW = NOW.replace(microsecond=0)
HOUR_1 = dt.timedelta(hours=1)


class TestShifts(DrawAPITestMixin, APILiveServerTestCase):
    maxDiff = None
    base_url = "shifts"
    Model = Shifts
    Factory = ShiftsFactory

    def _transform_draw(self, draw, write_access):
        return {
            **super()._transform_draw(draw, write_access),
            "intervals": draw.intervals,
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

    def test_creation_invalid(self):
        response = self.create(participants=[])
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def test_creation_not_enough_intervals(self):
        response = self.create(
            intervals=[
                {"start_time": NOW, "end_time": NOW + HOUR_1},
                {"start_time": NOW + HOUR_1, "end_time": NOW + HOUR_1 * 2},
                {"start_time": NOW + HOUR_1 * 2, "end_time": NOW + HOUR_1 * 3},
                # {"start_time": NOW + HOUR_1*3, "end_time": NOW + HOUR_1*4},
            ],
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def test_toss_validate_response(self):
        draw = self.Factory(
            intervals=[
                {"start_time": NOW, "end_time": NOW + HOUR_1},
            ],
            participants=[dict(name="mario")],
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        result = response.json()["value"]
        assert result == [
            {
                "interval": {
                    "start_time": NOW.isoformat().replace("+00:00", "Z"),
                    "end_time": (NOW + HOUR_1).isoformat().replace("+00:00", "Z"),
                },
                "participants": [{"id": ANY, "name": "mario", "facebook_id": None}],
            }
        ]
