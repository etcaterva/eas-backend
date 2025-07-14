import contextlib
import datetime as dt
import functools
import json
import logging

import cachetools
import requests
import requests.adapters
from django.conf import settings

LAMADAVA_APIK = settings.LAMADAVA_APIK
LOG = logging.getLogger(__name__)
ONE_MINUTE = 60  # seconds


class NotFoundError(Exception):
    pass


class InvalidURL(Exception):
    pass


@functools.lru_cache(None)
def _session():  # pragma: no cover
    retry = requests.adapters.Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 503, 504, 520, 521, 522, 524],
    )
    s = requests.Session()
    s.mount("https://", requests.adapters.HTTPAdapter(max_retries=retry))
    return s


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
    except requests.exceptions.RequestException:
        LOG.info(
            "Failed to fetch comments via v2 API, falling back to gql", exc_info=True
        )
    return _fetch_comments_gql(media_pk)


@cachetools.cached(
    cachetools.TTLCache(
        maxsize=500,
        timer=dt.datetime.now,
        ttl=dt.timedelta(hours=1),
    )
)
def fetch_preview(url):  # pragma: no cover
    LOG.info("Fetching Instagram post preview for %s", url)
    response = _session().get(
        "https://api.lamadava.com/v1/media/by/url",
        params={
            "access_key": LAMADAVA_APIK,
            "url": url,
        },
        timeout=ONE_MINUTE * 2,
    )
    if not response.ok:
        LOG.warning("Failed lamadava post preview request! %s", response.text)
        with contextlib.suppress(KeyError, json.JSONDecodeError):
            if response.json()["exc_type"] in ("NotFoundError", "MediaNotFound"):
                raise NotFoundError(f"Post not found for {url}")
            if response.json()["exc_type"] in (
                "MediaUnavailable",
                "InvalidMediaId",
                "ValidationError",
            ):
                raise InvalidURL(f"Invalid id for instagram: {url}")
    response.raise_for_status()
    return response.json()


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
        with contextlib.suppress(KeyError, json.JSONDecodeError):
            if response.json()["exc_type"] == "NotFoundError":
                return []
            if response.json()["exc_type"] == "MediaUnavailable":
                raise InvalidURL(f"Invalid id for instagram: {media_pk}")
            if response.json()["exc_type"] == "CommentsDisabled":
                raise InvalidURL(f"Invalid id for instagram: {media_pk}")
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
    response.raise_for_status()
    return response.json()
