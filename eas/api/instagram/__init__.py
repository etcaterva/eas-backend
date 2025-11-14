import logging
import re
from dataclasses import dataclass

import instagrapi
import requests

from . import lamadava

LOG = logging.getLogger(__name__)
MENTION_RE = re.compile(r"(^|[^\w])@([\w\_\.]+)")
ONE_MINUTE = 60

NotFoundError = lamadava.NotFoundError
InvalidURL = lamadava.InvalidURL
InstagramTimeoutError = requests.exceptions.ConnectionError


@dataclass
class Comment:
    id: str
    text: str
    username: str
    userpic: str


_CLIENT = instagrapi.Client()


def _extract_media_pk(url):
    try:
        return _CLIENT.media_pk_from_url(url)
    except (ValueError, IndexError) as e:  # pragma: no cover
        LOG.info("Invalid instagram URL %r: %s", url, e)
        raise InvalidURL(f"Invalid URL: {url}") from e


def _fetch_comments(url):
    """Fetch all comments from instagram"""
    media_pk = _extract_media_pk(url)
    response = lamadava.fetch_comments(media_pk)
    LOG.info("Fetched %s comments for %s", len(response), url)
    if not response:  # pragma: no cover
        raise NotFoundError(f"No posts found for {url}")
    res = []
    for comment in response:
        try:
            res.append(
                Comment(
                    id=comment["pk"],
                    text=comment["text"],
                    username=comment["user"]["username"],
                    userpic=comment["user"]["profile_pic_url"],
                )
            )
        except KeyError as e:  # pragma: no cover
            LOG.error(
                "Comment does not contain field %s: %s", e, comment, exc_info=True
            )
    return res


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


@dataclass
class Preview:
    post_pic: str
    comment_count: int
    user_name: str
    user_pic: str
    caption_text: str


def get_preview(url):  # pragma:  no cover
    """Fetch preview information for an Instagram post"""
    preview_data = lamadava.fetch_preview(url)
    try:
        return Preview(
            comment_count=preview_data["comment_count"],
            user_name=preview_data["user"]["username"],
            user_pic=preview_data["user"]["profile_pic_url"],
            caption_text=preview_data["caption_text"],
            post_pic=preview_data["resources"][0]["thumbnail_url"]
            if preview_data["resources"]
            else preview_data["thumbnail_url"],
        )
    except (KeyError, IndexError) as e:
        LOG.error("Preview data invalid: %r. Data: %s", e, preview_data, exc_info=True)
        raise
