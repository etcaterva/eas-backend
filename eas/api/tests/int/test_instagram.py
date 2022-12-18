from unittest.mock import ANY, Mock, patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api import instagram, models
from eas.api.tests.int.common import DrawAPITestMixin
from eas.api.tests.int.test_purge import PurgeMixin

from .. import factories


@pytest.fixture(autouse=True)
def instagram_fake(request):  # pragma: no cover
    if "end2end" in request.keywords:
        yield
        return
    instagram._CLIENT.fetch_comments.cache_clear()  # pylint: disable=no-member,protected-access
    with patch("eas.api.instagram._CLIENT") as client:
        client.fetch_comments.return_value = [
            Mock(
                id="1",
                username="mariocj89",
                text="comment with a mention @dnaranjo89",
            ),
            Mock(
                id="2",
                username="dnaranjo89",
                text="Not a mention mariocj89@gmail.com",
            ),
            Mock(id="2", username="palvarez89", text="This rocks!"),
        ]
        yield client


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
        with patch("eas.api.instagram._CLIENT") as client:
            client.fetch_comments.side_effect = instagram.NotFoundError
            draw = self.Factory(
                prizes=[{"name": "cupcake"}], use_likes=False, min_mentions=0
            )
            url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
            response = self.client.post(url, {})
            self.assertEqual(
                response.status_code, status.HTTP_400_BAD_REQUEST, response.content
            )

    def test_timeout_on_post_fetch(self):
        with patch("eas.api.instagram._CLIENT") as client:
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

    @pytest.mark.skip
    def test_success_result_with_likes(self):  # pragma: no cover
        draw = self.Factory(
            prizes=[{"name": "cupcake"}], use_likes=True, min_mentions=0
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        assert response.json()["value"] == [
            {
                "prize": {"id": ANY, "name": "cupcake", "url": None},
                "comment": {
                    "id": ANY,
                    "username": "dnaranjo89",
                    "text": "Not a mention mariocj89@gmail.com",
                },
            }
        ]

    def test_success_result_with_mentions(self):
        draw = self.Factory(
            prizes=[{"name": "cupcake"}],
            use_likes=False,
            min_mentions=1,
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        assert response.json()["value"] == [
            {
                "prize": {"id": ANY, "name": "cupcake", "url": None},
                "comment": {
                    "id": ANY,
                    "username": "mariocj89",
                    "text": "comment with a mention @dnaranjo89",
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


@pytest.mark.end2end
@pytest.mark.skipif(
    instagram.DATALAMA_APIK == "datalama-apik",
    reason="Datalama APIK not set",
)
def test_instagram_api_integration():  # pragma: no cover
    test_url = "https://www.instagram.com/p/Cix1MFjj5Q4/"

    post_info = instagram.get_post_info(test_url)
    assert post_info["thumbnail"]
    assert post_info["likes"] >= 100
    assert post_info["comments"] > 15

    comments = list(instagram.get_comments(test_url))
    users = {c.username for c in comments}
    assert "melanicf" in users
    assert len(comments) > 15

    comments = list(instagram.get_comments(test_url, min_mentions=1))
    users = {c.username for c in comments}
    assert {"efphotographers"} == users

    comments = list(instagram.get_comments(test_url, min_mentions=2))
    users = {c.username for c in comments}
    assert set() == users
