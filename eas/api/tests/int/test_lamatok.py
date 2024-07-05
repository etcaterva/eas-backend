# pylint: disable=redefined-outer-name
import os
import pathlib
import unittest.mock

import pytest
import requests_mock

from eas.api.tiktok import InvalidURL, NotFoundError, get_comments

RESPONSES_PATH = pathlib.Path(__file__, "..", "data").resolve()
SUCCESS_RESPONSE = RESPONSES_PATH.joinpath("lamatok-success-response.json").read_text()


@pytest.fixture
def requestsm():
    if "EAS_LAMATOK_APIK" in os.environ:  # pragma: no cover
        yield unittest.mock.Mock()  # Dummy
        return
    with requests_mock.Mocker() as m:
        yield m


def test_success_response(requestsm):
    url = "https://www.tiktok.com/@fanmallorcashopping/video/7385245034506964257"
    requestsm.get(
        "https://api.lamatok.com/v1/media/comments/by/id", text=SUCCESS_RESPONSE
    )
    comments = get_comments(url)
    assert len(comments) == 20


def test_post_no_comments(requestsm):
    url = "https://www.tiktok.com/@echaloasuerte/video/7382573284749102368"
    requestsm.get(
        "https://api.lamatok.com/v1/media/comments/by/id",
        status_code=404,
        text='{"detail":"Comments (or media) Not found","exc_type":"CommentsNotFoundError","tt_status_code":0}',
    )
    with pytest.raises(NotFoundError):
        get_comments(url)


def test_fail_on_fake_url(requestsm):
    url = "https://www.tiktok.com/@echaloasuerte/video/7382573284749102369"
    requestsm.get(
        "https://api.lamatok.com/v1/media/comments/by/id",
        status_code=404,
        text='{"detail":"Comments (or media) Not found","exc_type":"CommentsNotFoundError","tt_status_code":0}',
    )
    with pytest.raises(NotFoundError):
        get_comments(url)


def test_fail_on_invalid_url(requestsm):
    url = "http://totallyfakeurl"
    requestsm.get(url)
    with pytest.raises(InvalidURL):
        get_comments(url)


def test_min_mentions_filter(requestsm):
    url = "https://www.tiktok.com/@fanmallorcashopping/video/7385245034506964257"
    requestsm.get(
        "https://api.lamatok.com/v1/media/comments/by/id", text=SUCCESS_RESPONSE
    )
    comments = get_comments(url, min_mentions=1)
    assert len(comments) == 17
    comments = get_comments(url, min_mentions=2)
    assert len(comments) == 13
    comments = get_comments(url, min_mentions=3)
    assert len(comments) == 0
