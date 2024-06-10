import contextlib
import datetime as dt
import functools
import logging

import cachetools
import requests
from django.conf import settings

LAMADAVA_APIK = settings.LAMADAVA_APIK
LOG = logging.getLogger(__name__)
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
    try:
        return _fetch_comments_v2(media_pk)
    except Exception:  # pylint: disable=W0703
        LOG.info(
            "Failed to fetch comments via v2 API, falling back to gql", exc_info=True
        )
    return _fetch_comments_gql(media_pk)


def _fetch_comments_v2(media_pk):  # pragma: no cover
    LOG.info("Sending request to lamadava for %s", media_pk)
    response = _session().get(
        "https://api.lamadava.com/v2/media/comments",
        params={
            "id": media_pk,
            "access_key": LAMADAVA_APIK,
        },
        timeout=ONE_MINUTE * 2,
    )
    if not response.ok:
        LOG.warning("Failed lamadava request! %s", response.text)
        with contextlib.suppress(Exception):
            if response.json()["exc_type"] in ("NotFoundError", "MediaUnavailable"):
                return []
    response.raise_for_status()
    try:
        return response.json()["response"]["comments"]
    except KeyError:
        LOG.warning("Failed lamadava request! %s", response.text)
        raise


def _fetch_comments_gql(media_pk):  # pragma: no cover
    LOG.info("Sending request to lamadava for %s", media_pk)
    response = _session().get(
        "https://api.lamadava.com/gql/comments",
        params={
            "media_id": media_pk,
            "amount": 50,
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
