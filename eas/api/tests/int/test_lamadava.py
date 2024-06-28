# pylint: disable=redefined-outer-name
import os
import pathlib
import unittest.mock

import pytest
import requests_mock

from eas.api.instagram import InvalidURL, NotFoundError, get_comments

RESPONSES_PATH = pathlib.Path(__file__, "..", "data").resolve()
SUCCESS_GQL_RESPONSE = RESPONSES_PATH.joinpath(
    "lamadava-success-gql-response.json"
).read_text()
SUCCESS_V2_RESPONSE = RESPONSES_PATH.joinpath(
    "lamadava-success-v2-response.json"
).read_text()
SUCCESS_V2_WITH_MENTIONS_RESPONSE = RESPONSES_PATH.joinpath(
    "lamadava-success-v2-mentions-response.json"
).read_text()


@pytest.fixture
def requestsm():
    if "EAS_LAMADAVA_APIK" in os.environ:  # pragma: no cover
        yield unittest.mock.Mock()  # Dummy
        return
    with requests_mock.Mocker() as m:
        yield m


def test_success_v2_response(requestsm):
    url = "https://www.instagram.com/p/C8eqdxpoiDz/"
    requestsm.get(
        "https://api.lamadava.com/v2/media/comments", text=SUCCESS_V2_RESPONSE
    )
    comments = get_comments(url)
    assert len(comments) == 15


def test_success_gql_response(requestsm):
    url = "https://www.instagram.com/p/C8eqdxpoiDz/"
    requestsm.get(
        "https://api.lamadava.com/v2/media/comments", text="error", status_code=500
    )
    requestsm.get("https://api.lamadava.com/gql/comments", text=SUCCESS_GQL_RESPONSE)
    comments = get_comments(url)
    assert len(comments) == 15


def test_post_no_comments(requestsm):
    url = "https://www.instagram.com/p/CzgloCRsPIl/"
    requestsm.get(
        "https://api.lamadava.com/v2/media/comments",
        status_code=404,
        text='{"detail":"Entries not found","exc_type":"NotFoundError"}',
    )
    requestsm.get(
        "https://api.lamadava.com/gql/comments",
        status_code=404,
        text='{"detail":"Entries not found","exc_type":"NotFoundError"}',
    )
    with pytest.raises(NotFoundError):
        get_comments(url)


def test_fail_on_private_account(requestsm):
    url = "https://www.instagram.com/p/C6jbcNBK6zwDScW9N8vKY5kdwG-qG5WsveB_jc0/"
    requestsm.get(
        "https://api.lamadava.com/v2/media/comments",
        status_code=404,
        text='{"detail":"Media is unavailable","exc_type":"MediaUnavailable"}',
    )
    requestsm.get(
        "https://api.lamadava.com/gql/comments",
        status_code=404,
        text='{"detail":"Entries not found","exc_type":"NotFoundError"}',
    )
    with pytest.raises(InvalidURL):
        get_comments(url)


def test_fail_on_fake_url(requestsm):
    url = "https://www.instagram.com/p/fake-url-for-sure/"
    requestsm.get(
        "https://api.lamadava.com/v2/media/comments",
        status_code=404,
        text='{"detail":"Media is unavailable","exc_type":"MediaUnavailable"}',
    )
    requestsm.get(
        "https://api.lamadava.com/gql/comments",
        status_code=404,
        text='{"detail":"Entries not found","exc_type":"NotFoundError"}',
    )
    with pytest.raises(InvalidURL):
        get_comments(url)


def test_min_mentions_filter(requestsm):
    url = "https://www.instagram.com/p/C6oslgUrIkU/"
    requestsm.get(
        "https://api.lamadava.com/v2/media/comments",
        text=SUCCESS_V2_WITH_MENTIONS_RESPONSE,
    )
    comments = get_comments(url, min_mentions=1)
    assert len(comments) == 5
    comments = get_comments(url, min_mentions=2)
    assert len(comments) == 0
