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
            Mock(user=Mock(username="mariocj89")),
            Mock(user=Mock(username="dnaranjo89")),
            Mock(user=Mock(username="palvarez89")),
        ]
        client.media_likers.return_value = [
            Mock(username="mariocj89"),
            Mock(username="dnaranjo89"),
            Mock(username="palvarez89"),
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
            "use_comments": draw.use_comments,
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

    def test_success_result_comments(self):
        draw = self.Factory(
            prizes=[{"name": "cupcake"}], use_comments=True, use_likes=False
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        assert response.json()["value"] == [
            {
                "prize": {"id": ANY, "name": "cupcake", "url": None},
                "participant": {"name": ANY},
            }
        ]

    def test_success_result_likes(self):
        draw = self.Factory(
            prizes=[{"name": "cupcake"}], use_comments=False, use_likes=True
        )
        url = reverse(f"{self.base_url}-toss", kwargs=dict(pk=draw.private_id))
        response = self.client.post(url, {})
        assert response.json()["value"] == [
            {
                "prize": {"id": ANY, "name": "cupcake", "url": None},
                "participant": {"name": ANY},
            }
        ]

    def test_create_invalid_combination(self):
        response = self.create(use_comments=False, use_likes=False)
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def test_create_invalid_no_prizes(self):
        response = self.create(prizes=[])
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )


@pytest.mark.end2end
def test_instagram_api_integration():
    test_url = "https://www.instagram.com/p/Cix1MFjj5Q4/?igshid=MDJmNzVkMjY%3D"
    post_info = instagram.get_post_info(test_url)
    likes = instagram.get_likes(test_url)
    comments = instagram.get_comments(test_url)
    assert post_info["thumbnail"]
    assert post_info["likes"] >= 100
    assert post_info["comments"] > 15
    assert len(likes) >= 100
    assert "melanicf" in comments
    assert len(comments) > 15
    assert "manuel_cantonero" in likes
