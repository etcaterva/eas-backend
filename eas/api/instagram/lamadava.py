import contextlib
import datetime as dt
import functools
import logging

import cachetools
import requests
from django.conf import settings

LAMADAVA_APIK = settings.LAMADAVA_APIK
LOG = logging.getLogger(__name__)
MAX_PAGE_LAMADAVA = 50
ONE_MINUTE = 60  # seconds


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
    LOG.info("Sending request to lamadava for %s", media_pk)
    response = _session().get(
        "https://api.lamadava.com/gql/comments",
        params={
            "media_id": media_pk,
            "amount": MAX_PAGE_LAMADAVA,
            "access_key": LAMADAVA_APIK,
        },
        timeout=ONE_MINUTE * 2,
    )
    if not response.ok:
        LOG.warning("Failed lamadava request! %s", response.text)
        with contextlib.suppress(Exception):
            if response.json()["exc_type"] == "NotFoundError":
                return []
    response.raise_for_status()
    return response.json()
