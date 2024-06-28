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


COMMENT = instagram.Comment(
    id="id1",
    text="comment",
    username="username",
    userpic="userpic",
)

COMMENT_WITH_MENTION = instagram.Comment(
    id="id2",
    text="comment with @mention",
    username="username2",
    userpic="userpic2",
)

COMMENT_WITH_MENTION2 = instagram.Comment(
    id="id3",
    text="comment with @mention3",
    username="username3",
    userpic="userpic3",
)


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

    @patch("eas.api.instagram.get_comments")
    def test_success_result_only_comments(self, instagram_mock):
        instagram_mock.return_value = [COMMENT]
        draw = self.Factory(
            prizes=[{"name": "cupcake"}], use_likes=False, min_mentions=0
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        assert response.json()["value"] == [
            {
                "prize": {"id": ANY, "name": "cupcake", "url": None},
                "comment": {"username": ANY, "text": ANY, "id": ANY, "userpic": ANY},
            }
        ]

    @patch("eas.api.instagram.get_comments")
    def test_toss_without_comments(self, instagram_mock):
        instagram_mock.side_effect = instagram.NotFoundError
        draw = self.Factory(
            prizes=[{"name": "cupcake"}], use_likes=False, min_mentions=0
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    @patch("eas.api.instagram.get_comments")
    def test_invalid_post_url(self, instagram_mock):
        instagram_mock.side_effect = instagram.InvalidURL
        draw = self.Factory(
            prizes=[{"name": "cupcake"}], use_likes=False, min_mentions=0
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    @patch("eas.api.instagram.get_comments")
    def test_instagram_timeout(self, instagram_mock):
        instagram_mock.side_effect = instagram.InstagramTimeoutError
        draw = self.Factory(
            prizes=[{"name": "cupcake"}], use_likes=False, min_mentions=0
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch("eas.api.instagram.get_comments")
    def test_create_invalid_no_prizes(self, instagram_mock):
        instagram_mock.return_value = [COMMENT]
        response = self.create(prizes=[])
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    @patch("eas.api.instagram.get_comments")
    def test_retoss_without_toss_fails(self, instagram_mock):
        instagram_mock.return_value = [COMMENT]
        draw = self.Factory(
            prizes=[{"name": "cupcake"}], use_likes=False, min_mentions=0
        )
        url = reverse(f"{self.base_url}-retoss", kwargs=dict(pk=draw.private_id))
        response = self.client.patch(url, {"prize_id": "asd"})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    @patch("eas.api.instagram.get_comments")
    def test_retoss_invalid_prize_fails(self, instagram_mock):
        instagram_mock.return_value = [COMMENT]
        draw = self.Factory(
            prizes=[{"name": "cupcake"}], use_likes=False, min_mentions=0
        )
        self.client.post(
            reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id)), {}
        )

        url = reverse(f"{self.base_url}-retoss", kwargs=dict(pk=draw.private_id))
        response = self.client.patch(url, {"prize_id": "asd"})
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    @patch("eas.api.instagram.get_comments")
    def test_retoss_success(self, instagram_mock):
        instagram_mock.return_value = [
            COMMENT,
            COMMENT_WITH_MENTION,
            COMMENT_WITH_MENTION2,
        ]
        draw = self.Factory(
            prizes=[{"name": "cupcake1"}, {"name": "cupcake2"}],
            use_likes=False,
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


class TestInstagramPurge(PurgeMixin, APILiveServerTestCase):
    FACTORY = factories.InstagramFactory
