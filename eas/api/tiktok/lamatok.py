import contextlib
import datetime as dt
import functools
import logging

import cachetools
import requests
from django.conf import settings

LAMATOK_APIK = settings.LAMATOK_APIK
LOG = logging.getLogger(__name__)
MAX_PAGE_LAMATOK = 100
ONE_MINUTE = 60  # seconds


class NotFoundError(Exception):
    pass


class InvalidURL(Exception):
    pass


@functools.lru_cache(None)
def _session():  # pragma: no cover
    return requests.Session()


@cachetools.cached(
    cachetools.TTLCache(
        maxsize=500,
        timer=dt.datetime.now,
        ttl=dt.timedelta(hours=1),
    )
)
def fetch_comments(media_pk):  # pragma: no cover
    LOG.info("Sending request to lamatok for %s", media_pk)
    response = _session().get(
        "https://api.lamatok.com/v1/media/comments/by/id",
        params={
            "id": media_pk,
            "count": MAX_PAGE_LAMATOK,
            "access_key": LAMATOK_APIK,
            # "cursor": None # We could page here
        },
        timeout=ONE_MINUTE * 2,
    )
    if not response.ok:
        LOG.warning("Failed lamatok request! %s", response.text)
        with contextlib.suppress(Exception):
            if response.json()["exc_type"] == "CommentsNotFoundError":
                return []
    response.raise_for_status()
    return response.json()["comments"]
