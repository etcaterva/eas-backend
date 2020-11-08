import datetime as dt
import json

import dateutil.parser
from django.urls import reverse
from rest_framework import status


class CustomJsonEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time, decimal types, and
    UUIDs.
    """

    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, dt.datetime):
            r = o.isoformat()
            if r.endswith("+00:00"):
                r = r[:-6] + "Z"
            return r
        return super().default(o)  # pragma: no cover


def to_plain_dict(in_dict):
    """Converts all values to a plain dict.

    Swaps datetime by str
    """
    return json.loads(json.dumps(in_dict, cls=CustomJsonEncoder))


class DrawAPITestMixin:
    maxDiff = None
    base_url = None
    Model = None
    Factory = None

    def setUp(self):
        self.draws = self.Factory.create_batch(size=50)
        self.draw = self.Factory()  # pylint: disable=not-callable
        self.client.default_format = "json"

    def get_draw(self, id_):
        return self.Model.objects.get(id=id_)

    def _transform_draw(self, draw, write_access):  # pylint: disable=no-self-use
        result = {
            "id": draw.id,
            "created_at": draw.created_at,
            "updated_at": draw.updated_at,
            "title": draw.title,
            "description": draw.description,
            "metadata": [],
            "results": [
                dict(
                    created_at=r.created_at,
                    value=r.value,
                    schedule_date=r.schedule_date,
                )
                for r in draw.results.order_by("-created_at")
            ],
        }

        if write_access:
            result["private_id"] = draw.private_id
        return result

    def create(self, **data):
        url = reverse(f"{self.base_url}-list")
        data = self.Factory.dict(**data)
        return self.client.post(url, data)

    def as_expected_result(self, draw, write_access=False):
        return to_plain_dict(self._transform_draw(draw, write_access))

    def success_create(self, **data):
        response = self.create(**data)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )
        return response

    def test_creation(self):
        response = self.success_create()
        db_draw = self.get_draw(response.data["id"])
        expected_result = self.as_expected_result(db_draw, write_access=True)
        self.assertEqual(response.data.keys(), expected_result.keys())
        self.assertEqual(response.data, expected_result)

    def test_retrieve(self):
        self.draw.toss()
        url = reverse(f"{self.base_url}-detail", kwargs=dict(pk=self.draw.id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        expected_result = self.as_expected_result(self.draw)
        self.assertEqual(response.data.keys(), expected_result.keys())
        self.assertEqual(response.data, expected_result)

    def test_retrieve_with_private_id(self):
        self.draw.toss()
        url = reverse(f"{self.base_url}-detail", kwargs=dict(pk=self.draw.private_id))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        expected_result = self.as_expected_result(self.draw, write_access=True)
        self.assertEqual(response.data.keys(), expected_result.keys())
        self.assertEqual(response.data, expected_result)

    def test_toss(self):
        url = reverse(
            f"{self.base_url}-toss", kwargs=dict(pk=str(self.draw.private_id))
        )
        toss_response = self.client.post(url)

        self.assertEqual(
            toss_response.status_code, status.HTTP_200_OK, toss_response.content
        )
        self.assertEqual(toss_response.data["value"], self.draw.results.first().value)

        url = reverse(f"{self.base_url}-detail", kwargs=dict(pk=self.draw.id))
        response = self.client.get(url)
        expected_result = self.as_expected_result(self.draw)
        self.assertEqual(response.data.keys(), expected_result.keys())
        self.assertEqual(1, len(response.data["results"]))
        self.assertEqual(response.data, expected_result)

    def test_schedule_future_toss(self):
        url = reverse(
            f"{self.base_url}-toss", kwargs=dict(pk=str(self.draw.private_id))
        )
        target_date = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)
        toss_response = self.client.post(
            url,
            {
                "schedule_date": target_date,
            },
        )

        self.assertEqual(
            toss_response.status_code, status.HTTP_200_OK, toss_response.content
        )
        self.assertEqual(toss_response.data["value"], self.draw.results.first().value)

        url = reverse(f"{self.base_url}-detail", kwargs=dict(pk=self.draw.id))
        response = self.client.get(url)
        expected_result = self.as_expected_result(self.draw)
        self.assertEqual(response.data.keys(), expected_result.keys())
        self.assertEqual(1, len(response.data["results"]))
        self.assertEqual(response.data, expected_result)

        result = response.data["results"][0]
        self.assertEqual(target_date, dateutil.parser.parse(result["schedule_date"]))
        self.assertIsNone(result["value"])

    def test_schedule_past_toss(self):
        url = reverse(
            f"{self.base_url}-toss", kwargs=dict(pk=str(self.draw.private_id))
        )
        target_date = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
        toss_response = self.client.post(
            url,
            {
                "schedule_date": target_date,
            },
        )

        self.assertEqual(
            toss_response.status_code, status.HTTP_200_OK, toss_response.content
        )
        self.assertEqual(toss_response.data["value"], self.draw.results.first().value)

        url = reverse(f"{self.base_url}-detail", kwargs=dict(pk=self.draw.id))
        response = self.client.get(url)
        expected_result = self.as_expected_result(self.draw)
        self.assertEqual(response.data.keys(), expected_result.keys())
        self.assertEqual(1, len(response.data["results"]))
        self.assertEqual(response.data, expected_result)

        result = response.data["results"][0]
        self.assertEqual(target_date, dateutil.parser.parse(result["schedule_date"]))
        self.assertIsNotNone(result["value"])

    def test_create_and_retrieve_metadata(self):
        response = self.success_create(
            metadata=[
                dict(client="web", key="chat_enabled", value="false"),
                dict(client="web", key="premium_customer", value="true"),
            ]
        )
        (chat_enabled_data,) = [
            i for i in response.data["metadata"] if i["key"] == "chat_enabled"
        ]
        self.assertEqual(
            chat_enabled_data, dict(client="web", key="chat_enabled", value="false")
        )
