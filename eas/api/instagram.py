import datetime as dt
import logging
import re
from dataclasses import dataclass

import cachetools
import instagrapi
import requests
from django.conf import settings

LOG = logging.getLogger(__name__)

MENTION_RE = re.compile(r"(^|[^\w])@([\w\_\.]+)")

DATALAMA_APIK = settings.DATALAMA_APIK

ONE_MINUTE = 60


class NotFoundError(Exception):
    pass


InstagramTimeoutError = requests.exceptions.ConnectionError


@dataclass
class _Comment:
    id: str
    text: str
    username: str


def str_bounded(obj):  # pragma: no cover
    obj_str = str(obj)
    if len(obj_str) < 200:
        return obj_str
    return obj_str[:180] + "[...]" + obj_str[-10:]


class _Client:
    def __init__(self):
        self._client = instagrapi.Client()
        self._session = requests.Session()

    @cachetools.cached(
        cachetools.TTLCache(
            maxsize=500,
            timer=dt.datetime.now,
            ttl=dt.timedelta(hours=1),
        )
    )
    def fetch_comments(self, url):  # pragma: no cover
        media_pk = self._client.media_pk_from_url(url)
        response = self._session.get(
            "https://api.lamadava.com/gql/comments",
            params={
                "media_id": media_pk,
                "amount": 1000,
                "access_key": DATALAMA_APIK,
            },
            timeout=ONE_MINUTE * 2,
        )
        LOG.info(
            "Fetch comments for %s, response %s", url, str_bounded(response.json())
        )
        if response.status_code == 403:
            LOG.critical("Out of lamadava quota! %s", response.json())
        response.raise_for_status()
        if not response.json():
            raise NotFoundError(f"No posts found for {url}")
        return [
            _Comment(
                id=comment["id"],
                text=comment["text"],
                username=comment["owner"]["username"],
            )
            for comment in response.json()
        ]


_CLIENT = _Client()


def get_comments(url, min_mentions=0, require_like=False):  # pragma: no cover
    LOG.info("Fetching comments for %r", url)
    for comment in _CLIENT.fetch_comments(url):
        if len(MENTION_RE.findall(comment.text)) < min_mentions:
            continue
        if require_like:
            raise NotImplementedError("Not implemented")
        yield comment
