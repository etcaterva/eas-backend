import functools
import logging

import instagrapi
import instagrapi.exceptions
from django.conf import settings

LOG = logging.getLogger(__name__)

MAX_COMMENT_RETRIEVE = 100


def _get_instagram_login():  # pragma: no cover
    return settings.INSTAGRAM_USERNAME, settings.INSTAGRAM_PASSWORD


@functools.lru_cache
def _get_client():  # pragma: no cover
    client = instagrapi.Client()
    username, password = _get_instagram_login()
    LOG.info("Log in instagram with username %r", username)
    client.login(username, password)
    return client


def _refresh_client_on_error(func):  # pragma: no cover
    @functools.wraps(func)
    def _(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except instagrapi.exceptions.ClientError:
            _get_client.cache_clear()
        return func(*args, **kwargs)

    return _


@_refresh_client_on_error
def get_post_info(url):
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
def get_likes(url):
    LOG.info("Fetching likes for %r", url)
    client = _get_client()
    media_pk = client.media_pk_from_url(url)
    result = list({c.username for c in client.media_likers(media_pk)})
    LOG.info("Got %r likes for %r", len(result), url)
    return result


@_refresh_client_on_error
def get_comments(url):
    LOG.info("Fetching comments for %r", url)
    client = _get_client()
    media_pk = client.media_pk_from_url(url)
    result = list(
        {c.user.username for c in client.media_comments(media_pk, MAX_COMMENT_RETRIEVE)}
    )
    LOG.info("Got %r comments for %r", len(result), url)
    return result
