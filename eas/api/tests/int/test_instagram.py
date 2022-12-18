import json
import pathlib
from unittest.mock import ANY, patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api import instagram, models
from eas.api.tests.int.common import DrawAPITestMixin
from eas.api.tests.int.test_purge import PurgeMixin

from .. import factories


@pytest.fixture(autouse=True)
def lamadava_fake():
    with pathlib.Path(
        __file__, "..", "data", "lamadava-response.json"
    ).resolve().open() as f:
        lamadava_response = json.load(f)
        with patch("eas.api.instagram.lamadava") as lamadava_mock:
            lamadava_mock.fetch_comments.return_value = lamadava_response
            yield lamadava_mock


class TestInstagram(DrawAPITestMixin, APILiveServerTestCase):
    maxDiff = None
    base_url = "instagram"
    Model = models.Instagram
    Factory = factories.InstagramFactory

    def _transform_draw(self, draw, write_access):
        return {
            **super()._transform_draw(draw, write_access),
            "post_url": draw.post_url,
            "use_likes": draw.use_likes,
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

    def test_success_result_only_comments(self):
        draw = self.Factory(
            prizes=[{"name": "cupcake"}], use_likes=False, min_mentions=0
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        assert response.json()["value"] == [
            {
                "prize": {"id": ANY, "name": "cupcake", "url": None},
                "comment": {"username": ANY, "text": ANY, "id": ANY},
            }
        ]

    def test_invalid_post_url(self):
        with patch("eas.api.instagram.lamadava") as client:
            client.fetch_comments.return_value = []
            draw = self.Factory(
                prizes=[{"name": "cupcake"}], use_likes=False, min_mentions=0
            )
            url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
            response = self.client.post(url, {})
            self.assertEqual(
                response.status_code, status.HTTP_400_BAD_REQUEST, response.content
            )

    def test_timeout_on_post_fetch(self):
        with patch("eas.api.instagram.lamadava") as client:
            client.fetch_comments.side_effect = instagram.InstagramTimeoutError
            draw = self.Factory(
                prizes=[{"name": "cupcake"}], use_likes=False, min_mentions=0
            )
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
            use_likes=False,
            min_mentions=4,
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        assert response.json()["value"] == [
            {
                "prize": {"id": ANY, "name": "cupcake", "url": None},
                "comment": {
                    "id": ANY,
                    "username": "cristy_tarrias",
                    "text": "Para tí Miguel 🔥 @onenomimi @arooa91 @luciita1588 @sheiila.aliiehs",
                },
            }
        ]

    def test_create_invalid_no_prizes(self):
        response = self.create(prizes=[])
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )


class TestInstagramPurge(PurgeMixin, APILiveServerTestCase):
    FACTORY = factories.InstagramFactory


def test_instagram_api_integration():
    test_url = "https://www.instagram.com/p/CjvSI1HMQ6J/"

    comments = list(instagram.get_comments(test_url))
    users = {c.username for c in comments}
    assert len(comments) >= 50
    assert "alicia_garcia11" in users

    comments = list(instagram.get_comments(test_url, min_mentions=2))
    users = {c.username for c in comments}
    assert {"cristy_tarrias"} == users

    comments = list(instagram.get_comments(test_url, min_mentions=20))
    users = {c.username for c in comments}
    assert set() == users
