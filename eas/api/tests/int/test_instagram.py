from unittest.mock import ANY, Mock, patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api import instagram, models
from eas.api.tests.int.common import DrawAPITestMixin

from .. import factories


@pytest.fixture(autouse=True)
def instagram_fake(request):
    if "end2end" in request.keywords:
        yield
        return
    with patch("eas.api.instagram._get_client") as instagram_get_client:
        client = instagram_get_client.return_value
        client.media_pk_from_url.return_value = 1234
        client.media_info.return_value = Mock(
            like_count=1, comment_count=2, thumbnail_url="url"
        )
        client.media_comments.return_value = [
            Mock(
                user=Mock(username="mariocj89"),
                text="comment with a mention @dnaranjo89",
                has_liked=False,
            ),
            Mock(
                user=Mock(username="dnaranjo89"),
                text="Not a mention mariocj89@gmail.com",
                has_liked=True,
            ),
            Mock(user=Mock(username="palvarez89"), text="This rocks!", has_liked=False),
        ]
        client.media_likers.return_value = [
            Mock(username="perico77"),
            Mock(username="raul66"),
            Mock(username="ficus123"),
        ]
        yield client


class TestInstagramPreview(APILiveServerTestCase):
    def setUp(self):
        self.client.default_format = "json"
        self.url = reverse("instagram-preview")

    def test_preview_success(self):
        response = self.client.get(self.url, {"post_url": "test-instagram-post-url"})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        assert response.json() == {"comments": 2, "likes": 1, "thumbnail": "url"}

    def test_preview_not_found(self):
        with patch("eas.api.instagram.get_post_info") as instagram_mock:
            instagram_mock.side_effect = instagram.NotFoundError
            response = self.client.get(
                self.url, {"post_url": "test-instagram-post-url"}
            )
            self.assertEqual(
                response.status_code, status.HTTP_404_NOT_FOUND, response.content
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

    def test_success_result_only_comments(self):
        draw = self.Factory(
            prizes=[{"name": "cupcake"}], use_likes=False, min_mentions=0
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        assert response.json()["value"] == [
            {
                "prize": {"id": ANY, "name": "cupcake", "url": None},
                "comment": {"name": ANY, "text": ANY},
            }
        ]

    def test_success_result_with_likes(self):
        draw = self.Factory(
            prizes=[{"name": "cupcake"}], use_likes=True, min_mentions=0
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        assert response.json()["value"] == [
            {
                "prize": {"id": ANY, "name": "cupcake", "url": None},
                "comment": {
                    "name": "dnaranjo89",
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
                    "name": "mariocj89",
                    "text": "comment with a mention @dnaranjo89",
                },
            }
        ]

    def test_create_invalid_no_prizes(self):
        response = self.create(prizes=[])
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )


try:
    instagram._get_client()  # pylint: disable=protected-access
except Exception:  # pylint: disable=broad-except
    instagrap_api_works = False
else:
    instagrap_api_works = True


@pytest.mark.end2end
@pytest.mark.skipif(
    not instagrap_api_works, reason="Unable to create an instagram API client."
)
def test_instagram_api_integration():
    test_url = "https://www.instagram.com/p/Cix1MFjj5Q4/?igshid=MDJmNzVkMjY%3D"

    post_info = instagram.get_post_info(test_url)
    assert post_info["thumbnail"]
    assert post_info["likes"] >= 100
    assert post_info["comments"] > 15

    comments = instagram.get_comments(test_url)
    users = {c[0] for c in comments}
    assert "melanicf" in users
    assert len(comments) > 15

    comments = instagram.get_comments(test_url, min_mentions=1)
    users = {c[0] for c in comments}
    assert {"efphotographers", "melanicf"} == users

    comments = instagram.get_comments(test_url, min_mentions=2)
    users = {c[0] for c in comments}
    assert {"melanicf"} == users

    assert set() == instagram.get_comments(test_url, min_mentions=3)

    comments = instagram.get_comments(test_url, require_like=True)
    users = {c[0] for c in comments}
    assert {"songdeluxe"} == users
