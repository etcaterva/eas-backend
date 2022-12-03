import functools
import logging
import pathlib
import pickle
import re

import instagrapi
import instagrapi.exceptions
from django.conf import settings

from . import instagram_challenge

LOG = logging.getLogger(__name__)

MAX_COMMENT_RETRIEVE = 1000
MENTION_RE = re.compile(r"(^|[^\w])@([\w\_\.]+)")

NotFoundError = instagrapi.exceptions.NotFoundError


def _get_instagram_login():  # pragma: no cover
    user = settings.INSTAGRAM_EMAIL_USERNAME
    instagram_password_file = pathlib.Path(settings.INSTAGRAM_PASSWORD_FILE)
    if not instagram_password_file.exists():
        LOG.fatal(
            "%s does not exist. Create the file and set EAS_INSTAGRAM_EMAIL_USERNAME"
            " env var to develop locally",
            instagram_password_file,
        )
        raise RuntimeError("Instagram features cannot be used as it is not configured")
    password = instagram_password_file.read_text().strip()
    return user, password


def _get_instagram_cache():  # pragma: no cover
    try:
        with open(settings.INSTAGRAM_CACHE_FILE, "rb") as f:
            return pickle.load(f)
    except (FileNotFoundError, pickle.PickleError, EOFError):
        return None


def _set_instagram_cache(client):  # pragma: no cover
    with open(settings.INSTAGRAM_CACHE_FILE, "wb") as f:
        pickle.dump(client, f)


def _get_client():  # pragma: no cover
    client = _get_instagram_cache()
    if client is not None:
        return client

    client = instagrapi.Client()
    client.challenge_code_handler = instagram_challenge.challenge_code_handler
    username, password = _get_instagram_login()
    LOG.info("Log in instagram with username %r", username)
    client.login(username, password)
    LOG.info("Log in success")
    _set_instagram_cache(client)
    return client


def _refresh_client_on_error(func):  # pragma: no cover
    @functools.wraps(func)
    def _(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NotFoundError:  # pragma: no cover
            raise
        except instagrapi.exceptions.ClientError:
            _set_instagram_cache(None)
        return func(*args, **kwargs)

    return _


@_refresh_client_on_error
def get_post_info(url):  # pragma: no cover
    LOG.info("Fetching info for %r", url)
    client = _get_client()
    media_pk = client.media_pk_from_url(url)
    media_data = client.media_info(media_pk)
    try:
        thumbnail = media_data.thumbnail_url or media_data.resources[0].thumbnail_url
    except Exception:  # pragma: no cover  # pylint: disable=broad-except
        LOG.exception("Failed to get thumbnail from: %r", media_data)
        thumbnail = None
    ret = dict(
        likes=media_data.like_count,
        comments=media_data.comment_count,
        thumbnail=thumbnail,
    )
    LOG.info("Got info for %r", url)
    return ret


@_refresh_client_on_error
def get_comments(url, min_mentions=0, require_like=False):  # pragma: no cover
    LOG.info("Fetching comments for %r", url)
    client = _get_client()
    result = set()
    media_pk = client.media_pk_from_url(url)
    for comment in client.media_comments(media_pk, MAX_COMMENT_RETRIEVE):
        if len(MENTION_RE.findall(comment.text)) < min_mentions:
            continue
        if require_like and not comment.has_liked:
            continue
        result.add((comment.user.username, comment.text))
    LOG.info("Got %r comments for %r", len(result), url)
    return result
