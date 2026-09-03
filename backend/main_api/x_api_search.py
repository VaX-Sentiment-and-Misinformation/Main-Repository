#!/usr/bin/env python3
"""
x_api_search.py - fetch recent vaccine-related X posts via the official X API v2.

Uses GET /2/tweets/search/recent, which covers a rolling 7-day window, and returns
the highest-view posts from that window.

    from x_api_search import fetch_top_vaccine_posts

    posts = fetch_top_vaccine_posts(limit=10)   # top 10 by views

Two things worth knowing before you run this:

1. **The API cannot sort by views.** `search/recent` supports `sort_order=recency`
   or `relevancy` only. So this fetches a larger *pool* of recent matches and sorts
   them by `impression_count` locally. The top 10 are therefore the 10 most-viewed
   of the pool, not of every vaccine post on X in the last week. A bigger pool gives
   a better answer and costs more.

2. **It costs money.** The X API is pay-per-usage with no free tier, billed per post
   returned (about $0.005 each at the time of writing). `pool=100` is roughly $0.50 a
   run. Posts requested more than once in a 24h UTC window are only charged once.

Requires X_BEARER_TOKEN in backend/.env. Stdlib only, matching x_post_fetcher.py.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

__all__ = ["fetch_top_vaccine_posts", "search_recent", "XAPIError", "VACCINE_QUERY"]

SEARCH_URL = "https://api.x.com/2/tweets/search/recent"

# -is:retweet keeps retweets out: they duplicate the original's text and their
# metrics belong to the original post, which would skew a "most viewed" ranking.
VACCINE_QUERY = (
    '(vaccine OR vaccines OR vaccinated OR vaccination OR vax OR vaxxed '
    'OR antivax OR "covid vaccine" OR "flu shot") -is:retweet lang:en'
)

# The API caps a single page at 100.
MAX_PAGE = 100


class XAPIError(RuntimeError):
    """The X API rejected the request or isn't reachable."""


def _bearer_token() -> str:
    token = os.getenv("X_BEARER_TOKEN")
    if not token:
        raise XAPIError(
            "X_BEARER_TOKEN is not set. Create an app at developer.x.com, copy its "
            "Bearer Token, and add it to backend/.env as X_BEARER_TOKEN=..."
        )
    return token


def _get(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer %s" % _bearer_token(),
        "User-Agent": "vax-sentiment-research/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        if e.code == 401:
            raise XAPIError("401 Unauthorized - the bearer token is wrong or revoked.") from e
        if e.code == 403:
            raise XAPIError(
                "403 Forbidden - the token is valid but this project can't use recent "
                "search. Check the app's access level in the developer console. %s" % detail
            ) from e
        if e.code == 429:
            raise XAPIError(
                "429 Rate limited - you've hit the request cap for this window. "
                "Wait and retry, or lower `pool`."
            ) from e
        raise XAPIError("HTTP %s from the X API: %s" % (e.code, detail)) from e
    except urllib.error.URLError as e:
        raise XAPIError("Could not reach the X API: %s" % e.reason) from e


def _window_start(days: int = 7) -> str:
    """ISO 8601 start time, nudged inside the window.

    The endpoint rejects a start_time older than 7 days, and a start_time computed
    as exactly 7 days ago can land just outside it once the request is in flight,
    so back off by a minute.
    """
    start = datetime.now(timezone.utc) - timedelta(days=days) + timedelta(minutes=1)
    return start.strftime("%Y-%m-%dT%H:%M:%SZ")


def search_recent(query: str = VACCINE_QUERY, pool: int = MAX_PAGE, days: int = 7) -> list[dict]:
    """Pull up to `pool` recent posts matching `query`, newest first.

    Pages through the API in chunks of 100 as needed. Returns normalised dicts in
    the same shape as x_post_fetcher.fetch_post, so XPost.from_fetch works on them.
    """
    collected: list[dict] = []
    next_token = None

    while len(collected) < pool:
        want = min(MAX_PAGE, pool - len(collected))
        # The API's minimum page size is 10 even if we want fewer.
        params = {
            "query": query,
            "max_results": str(max(10, want)),
            "start_time": _window_start(days),
            "sort_order": "recency",
            "tweet.fields": ("created_at,public_metrics,lang,author_id,possibly_sensitive,"
                             "referenced_tweets,in_reply_to_user_id,attachments"),
            "expansions": "author_id,in_reply_to_user_id,attachments.media_keys",
            "user.fields": "name,username,public_metrics",
            "media.fields": "url,preview_image_url,type",
        }
        if next_token:
            params["next_token"] = next_token

        data = _get(SEARCH_URL + "?" + urllib.parse.urlencode(params))

        posts = data.get("data") or []
        if not posts:
            break
        includes = data.get("includes") or {}
        users = {u["id"]: u for u in includes.get("users", [])}
        media = {m["media_key"]: m for m in includes.get("media", [])}

        for raw in posts:
            collected.append(_normalise(raw, users, media))

        next_token = (data.get("meta") or {}).get("next_token")
        if not next_token:
            break

    return collected[:pool]


def _normalise(raw: dict, users: dict, media: dict) -> dict:
    """Map an API v2 post onto the dict shape x_post_fetcher returns."""
    metrics = raw.get("public_metrics") or {}
    author = users.get(raw.get("author_id")) or {}
    handle = author.get("username")

    referenced = {r.get("type"): r.get("id") for r in (raw.get("referenced_tweets") or [])}
    media_keys = (raw.get("attachments") or {}).get("media_keys") or []
    media_urls = []
    for key in media_keys:
        m = media.get(key) or {}
        url = m.get("url") or m.get("preview_image_url")
        if url:
            media_urls.append(url)

    reply_to_user = users.get(raw.get("in_reply_to_user_id")) or {}

    return {
        "id": raw.get("id"),
        "url": "https://x.com/%s/status/%s" % (handle or "i", raw.get("id")),
        # ISO 8601 from this endpoint, e.g. 2026-09-01T12:00:00.000Z, unlike the
        # legacy "Tue Mar 21 20:50:14 +0000 2006" the public backends return.
        # models.parse_x_time reads both.
        "created_at": raw.get("created_at"),
        "created_timestamp": None,
        "text": raw.get("text"),
        "lang": raw.get("lang"),
        "author_name": author.get("name"),
        "author_handle": handle,
        "author_id": raw.get("author_id"),
        "author_followers": (author.get("public_metrics") or {}).get("followers_count"),
        "replies": metrics.get("reply_count"),
        # X renamed retweets to reposts; accept whichever key comes back.
        "reposts": metrics.get("retweet_count", metrics.get("repost_count")),
        "likes": metrics.get("like_count"),
        "quotes": metrics.get("quote_count"),
        "views": metrics.get("impression_count"),
        "bookmarks": metrics.get("bookmark_count"),
        "is_reply_to": referenced.get("replied_to"),
        "reply_to_handle": reply_to_user.get("username"),
        "is_quote": "quoted" in referenced,
        "quoted_id": referenced.get("quoted"),
        "possibly_sensitive": raw.get("possibly_sensitive"),
        # The `source` field (the posting client) was removed from API v2.
        "source_client": None,
        "media_count": len(media_keys),
        "media_urls": media_urls,
        "has_poll": bool((raw.get("attachments") or {}).get("poll_ids")),
        # Community notes aren't exposed on this endpoint.
        "has_community_note": None,
        "_backend": "x-api-v2",
    }


def fetch_top_vaccine_posts(limit: int = 10, pool: int = MAX_PAGE,
                            query: str = VACCINE_QUERY, days: int = 7) -> list[dict]:
    """The `limit` most-viewed vaccine posts from the last `days` days.

    `pool` is how many recent posts to rank. Raising it gives a more representative
    top-10 and costs proportionally more, since billing is per post returned.
    Posts with no view count sort last rather than being treated as zero.
    """
    posts = search_recent(query=query, pool=pool, days=days)
    posts.sort(key=lambda p: (p["views"] is not None, p["views"] or 0), reverse=True)
    return posts[:limit]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    pool = int(argv[0]) if argv else MAX_PAGE

    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    except ImportError:
        pass

    try:
        posts = fetch_top_vaccine_posts(limit=10, pool=pool)
    except XAPIError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1

    if not posts:
        print("No matching posts in the last 7 days.", file=sys.stderr)
        return 1

    for i, p in enumerate(posts, 1):
        print("%2d. %-16s %10s views  %s" % (
            i, "@" + (p["author_handle"] or "?"),
            "{:,}".format(p["views"]) if p["views"] is not None else "n/a",
            (p["text"] or "").replace("\n", " ")[:70]))
    print("\n(ranked from a pool of %d recent posts)" % pool, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
