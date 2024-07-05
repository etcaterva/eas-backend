import json
import pathlib
from unittest.mock import ANY, patch

import pytest
import requests.exceptions
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api import models, tiktok
from eas.api.tests.int.common import DrawAPITestMixin
from eas.api.tests.int.test_purge import PurgeMixin

from .. import factories

COMMENT = tiktok.Comment(
    id="id",
    text="text",
    url="url",
    username="username",
    userid="userid",
    userpic="userpic",
)


@pytest.fixture(autouse=True)
def lamatok_fake():
    with pathlib.Path(
        __file__, "..", "data", "lamatok-response.json"
    ).resolve().open() as f:
        lamatok_response = json.load(f)["comments"]
        with patch("eas.api.tiktok.lamatok") as lamatok_mock:
            lamatok_mock.fetch_comments.return_value = lamatok_response
            yield lamatok_mock


class Testtiktok(DrawAPITestMixin, APILiveServerTestCase):
    maxDiff = None
    base_url = "tiktok"
    Model = models.Tiktok
    Factory = factories.TiktokFactory

    def _transform_draw(self, draw, write_access):
        return {
            **super()._transform_draw(draw, write_access),
            "post_url": draw.post_url,
            "min_mentions": draw.min_mentions,
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

    @patch("eas.api.tiktok.get_comments")
    def test_success_result_only_comments(self, tiktok_fake):
        tiktok_fake.return_value = [COMMENT]
        draw = self.Factory(prizes=[{"name": "cupcake"}], min_mentions=0)
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        assert response.json()["value"] == [
            {
                "prize": {"id": ANY, "name": "cupcake", "url": None},
                "comment": {
                    "username": ANY,
                    "userid": ANY,
                    "text": ANY,
                    "id": ANY,
                    "userpic": ANY,
                    "url": ANY,
                },
            }
        ]

    @patch("eas.api.tiktok.get_comments")
    def test_invalid_post_has_no_comments(self, tiktok_fake):
        tiktok_fake.side_effect = tiktok.NotFoundError
        draw = self.Factory()
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    @patch("eas.api.tiktok.get_comments")
    def test_toss_fails_invalid_post_url(self, tiktok_fake):
        tiktok_fake.side_effect = tiktok.InvalidURL
        draw = self.Factory(post_url="https://tiktok.com/user/@elputo")
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def test_post_url_redirect(self):
        draw = self.Factory(post_url="https://vm.tiktok.com/ZMrjQ8U3W/")
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    @patch("eas.api.tiktok.get_comments")
    def test_timeout_on_post_fetch(self, tiktok_fake):
        tiktok_fake.side_effect = requests.exceptions.ConnectionError
        draw = self.Factory(prizes=[{"name": "cupcake"}], min_mentions=0)
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            response.content,
        )

    def test_success_result_with_mentions(self):
        draw = self.Factory(
            prizes=[{"name": "cupcake"}],
            min_mentions=12,
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        assert response.json()["value"] == [
            {
                "prize": {"id": ANY, "name": "cupcake", "url": None},
                "comment": {
                    "id": "7367657284540089120",
                    "username": "pilipardoandujar",
                    "userid": "pilipardoandujar",
                    "userpic": ANY,
                    "text": ANY,
                    "url": ANY,
                },
            }
        ]

    @patch("eas.api.tiktok.get_comments")
    def test_create_invalid_no_prizes(self, tiktok_fake):
        tiktok_fake.side_effect = tiktok.InvalidURL
        response = self.create()
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    @patch("eas.api.tiktok.get_comments")
    def test_create_fails_with_invalid_url(self, tiktok_fake):
        tiktok_fake.side_effect = tiktok.InvalidURL
        response = self.create()
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    @patch("eas.api.tiktok.get_comments")
    def test_create_without_comments_works(self, tiktok_fake):
        tiktok_fake.side_effect = tiktok.NotFoundError
        response = self.create()
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

    def test_create_fails_with_invalid_prizes(self):
        response = self.create(prizes=[])
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def test_retoss_without_toss_fails(self):
        draw = self.Factory(prizes=[{"name": "cupcake"}], min_mentions=0)
        url = reverse(f"{self.base_url}-retoss", kwargs=dict(pk=draw.private_id))
        response = self.client.patch(url, {"prize_id": "asd"})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def test_retoss_invalid_prize_fails(self):
        draw = self.Factory(prizes=[{"name": "cupcake"}], min_mentions=0)
        self.client.post(
            reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id)), {}
        )

        url = reverse(f"{self.base_url}-retoss", kwargs=dict(pk=draw.private_id))
        response = self.client.patch(url, {"prize_id": "asd"})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def test_retoss_success(self):
        draw = self.Factory(
            prizes=[{"name": "cupcake1"}, {"name": "cupcake2"}],
            min_mentions=0,
        )
        self.client.post(
            reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id)), {}
        )
        draw.refresh_from_db()
        assert len(draw.results.all()) == 1

        item_to_repeat = draw.results.all()[0].value[0]
        url = reverse(f"{self.base_url}-retoss", kwargs=dict(pk=draw.private_id))
        self.client.patch(url, {"prize_id": item_to_repeat["prize"]["id"]})
        draw.refresh_from_db()
        assert len(draw.results.all()) == 2

        initial_result = draw.results.all()[0]
        retossed_result = draw.results.all()[1]

        assert retossed_result.created_at > initial_result.created_at
        assert retossed_result.value[0] != item_to_repeat
        assert initial_result.value[0] == item_to_repeat
        assert retossed_result.value[1] == initial_result.value[1]


class TesttiktokPurge(PurgeMixin, APILiveServerTestCase):
    FACTORY = factories.TiktokFactory
