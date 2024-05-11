import logging
import re
from dataclasses import dataclass

import requests

from . import lamatok

LOG = logging.getLogger(__name__)
MENTION_RE = re.compile(r"(^|[^\w])@([\w\_\.]+)")
TIKTOK_RE = re.compile(r"/video/([^?/&]*)")
ONE_MINUTE = 60


class NotFoundError(Exception):
    pass


TiktokTimeoutError = requests.exceptions.ConnectionError


@dataclass
class Comment:
    id: str
    text: str
    url: str
    username: str
    userpic: str
    userid: str


def _extract_media_pk(url):
    if match := TIKTOK_RE.search(url):
        return match.group(1)
    raise NotFoundError(f"Invalid tiktok URL {url}")


def _fetch_comments(url):
    """Fetch all comments from tiktok"""
    media_pk = _extract_media_pk(url)
    response = lamatok.fetch_comments(media_pk)
    LOG.info("Fetched %s comments for %s", len(response), url)
    if not response:
        raise NotFoundError(f"No posts found for {url}")
    res = []
    for comment in response:
        try:
            res.append(
                Comment(
                    id=comment["cid"],
                    url=comment["share_info"]["url"],
                    text=comment["text"],
                    username=comment["user"]["nickname"],
                    userpic=comment["user"]["avatar_thumb"]["url_list"][0],
                    userid=comment["user"]["unique_id"],
                )
            )
        except KeyError as e:  # pragma: no cover
            LOG.error(
                "Comment does not contain field %s: %s", e, comment, exc_info=True
            )
    return res


def get_comments(url, min_mentions=0):  # pragma: no cover
    """Fetch and filter comments"""
    LOG.info(
        "Fetching comments for %r, mentions=%s",
        url,
        min_mentions,
    )
    ret = []
    for comment in _fetch_comments(url):
        if len(MENTION_RE.findall(comment.text)) < min_mentions:
            continue
        ret.append(comment)
    LOG.info("%s comments match criteria for %s", len(ret), url)
    return ret
