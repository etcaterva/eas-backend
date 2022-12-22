import logging
import re
from dataclasses import dataclass

import instagrapi
import requests

from . import lamadava

LOG = logging.getLogger(__name__)
MENTION_RE = re.compile(r"(^|[^\w])@([\w\_\.]+)")
ONE_MINUTE = 60


class NotFoundError(Exception):
    pass


InstagramTimeoutError = requests.exceptions.ConnectionError


@dataclass
class Comment:
    id: str
    text: str
    username: str
    userpic: str


_CLIENT = instagrapi.Client()


def _extract_media_pk(url):
    return _CLIENT.media_pk_from_url(url)


def _fetch_comments(url):
    """Fetch all comments from instagram"""
    media_pk = _extract_media_pk(url)
    response = lamadava.fetch_comments(media_pk)
    LOG.info("Fetched %s comments for %s", len(response), url)
    if not response:
        raise NotFoundError(f"No posts found for {url}")
    return [
        Comment(
            id=comment["id"],
            text=comment["text"],
            username=comment["owner"]["username"],
            userpic=comment["owner"]["profile_pic_url"],
        )
        for comment in response
    ]


def get_comments(url, min_mentions=0, require_like=False):  # pragma: no cover
    """Fetch and filter comments"""
    LOG.info(
        "Fetching comments for %r, mentions=%s, require_like=%s",
        url,
        min_mentions,
        require_like,
    )
    ret = []
    for comment in _fetch_comments(url):
        if len(MENTION_RE.findall(comment.text)) < min_mentions:
            continue
        if require_like:
            raise NotImplementedError("Not implemented")
        ret.append(comment)
    LOG.info("%s comments match criteria for %s", len(ret), url)
    return ret
