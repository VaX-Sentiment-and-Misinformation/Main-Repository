#!/usr/bin/env python3
"""
x_api_search.py - fetch recent vaccine X posts via the official X API v2.

Uses GET /2/tweets/search/recent, which covers a rolling 7-day window, and returns
the most-liked posts of a pool from that window.

    from x_api_search import fetch_top_vaccine_posts

    posts = fetch_top_vaccine_posts(limit=10)   # 10 notable posts, by likes

Two things worth knowing before you run this:

1. **The API cannot sort by engagement at all.** `search/recent` supports
   `sort_order=recency` or `relevancy` only - there is no sort-by-likes, and the v2
   query syntax has no `min_faves:` operator either. So this fetches a *pool* and
   ranks it by `like_count` locally. The top 10 are the 10 most-liked of the pool,
   not of every vaccine post on X in the last week. Call `count_recent()` first -
   it returns no posts, so it is not billed per post - to see how much of the week
   your pool actually covers.

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

__all__ = ["fetch_top_vaccine_posts", "rank_posts", "search_recent", "count_recent",
           "save_run", "XAPIError", "VACCINE_QUERY"]

SEARCH_URL = "https://api.x.com/2/tweets/search/recent"
# Counts, unlike search, returns no posts - so it is not billed per post.
COUNTS_URL = "https://api.x.com/2/tweets/counts/recent"

# -is:retweet keeps retweets out: they duplicate the original's text and their
# metrics belong to the original post, which would skew a "most liked" ranking.
VACCINE_QUERY = (
    '(vaccine OR vaccines OR vaccinated OR vaccination OR vax OR vaxxed '
    'OR antivax OR "covid vaccine" OR "flu shot" OR immunization OR immunisation) '
    '-is:retweet lang:en'
)

# An HPV term AND a vaccine term, so posts about the virus or about cervical
# cancer screening don't come through — only posts about the vaccine do. The
# brand names and #HPVvaccine sit outside that pairing because they already
# name a vaccine on their own, and a hashtag is one token: the bare keyword
# HPV does not match #HPVvaccine.
# VACCINE_QUERY = (
#     '(((HPV OR papillomavirus OR "papilloma virus") '
#     '(vaccine OR vaccines OR vaccinated OR vaccination OR vax OR vaxxed '
#     'OR jab OR shot OR immunization OR immunisation)) '
#     'OR gardasil OR cervarix OR #HPVvaccine OR "cervical cancer vaccine") '
#     '-is:retweet lang:en'
# )

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
        if e.code == 402:
            raise XAPIError(
                "402 Payment Required - the token is valid, but this X API account "
                "has no credits left. Top up or pick a plan at developer.x.com. No "
                "endpoint works until then, counts included."
            ) from e
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
    """Pull up to `pool` posts matching `query` from the last `days` days.

    Ordered by the API's own relevance ranking, not by time, and not by any
    engagement metric - see `fetch_top_vaccine_posts` for the local ranking.
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
            # relevancy, not recency: X's relevance ranking factors in engagement,
            # so the pool we pay for skews towards the high-engagement posts this
            # module is looking for, instead of whatever happened to be posted in
            # the last few hours. That biases the pool, which would disqualify it
            # as a sample for the sentiment/misinformation models - their training
            # corpora under data/ are keyword-and-time sampled - but this path is
            # presentational, so the bias is the point.
            "sort_order": "relevancy",
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


def count_recent(query: str = VACCINE_QUERY, days: int = 7) -> int:
    """How many posts match `query` in the window.

    Returns counts, not posts, so the per-post billing that makes `search_recent`
    cost money does not apply - though the account still needs credits at all, or
    every endpoint 402s. Worth calling before a paid run: it says what fraction of
    the week a given `pool` covers, i.e. whether a "top 10" is the real top 10 or
    just the top 10 of a sample.
    """
    params = {
        "query": query,
        "start_time": _window_start(days),
        "granularity": "day",
    }
    data = _get(COUNTS_URL + "?" + urllib.parse.urlencode(params))
    return (data.get("meta") or {}).get("total_tweet_count", 0)


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


def _score(post: dict, metric: str):
    """Sort key for one post: (has a value, the value).

    The leading bool keeps posts with a missing count at the bottom instead of
    letting them tie with a genuine zero.
    """
    if metric == "likes":
        value = post["likes"]
    elif metric == "engagement":
        parts = [post["likes"], post["reposts"], post["replies"], post["quotes"]]
        value = sum(p for p in parts if p is not None) if any(
            p is not None for p in parts) else None
    else:
        raise ValueError("metric must be 'likes' or 'engagement', not %r" % metric)
    return (value is not None, value or 0)


def rank_posts(posts: list[dict], metric: str = "likes") -> list[dict]:
    """The whole pool, most-engaged first.

    Kept separate from `fetch_top_vaccine_posts` so a caller that paid for a pool
    can hold on to all of it - the CLI saves the full ranked list to JSON and only
    prints the head of it.
    """
    return sorted(posts, key=lambda p: _score(p, metric), reverse=True)


def fetch_top_vaccine_posts(limit: int = 10, pool: int = MAX_PAGE,
                            query: str = VACCINE_QUERY, days: int = 7,
                            metric: str = "likes") -> list[dict]:
    """The `limit` most-engaged vaccine posts *of the pool this fetches*.

    Not the most-engaged on X. The API cannot sort by engagement, so this ranks a
    pool that `search_recent` chose by relevance. Against a broad query that pool
    is a fraction of a percent of what actually matches - `count_recent()` will
    tell you what fraction - so treat the result as notable posts rather than a
    definitive top-10. Raising `pool` narrows the gap and costs proportionally
    more, since billing is per post returned.

    `metric` picks what "engaged" means: "likes" (the default) ranks on likes
    alone, "engagement" on likes + reposts + replies + quotes. Posts missing that
    count sort last rather than being treated as zero.
    """
    return rank_posts(search_recent(query=query, pool=pool, days=days), metric)[:limit]


USAGE = """usage: x_api_search.py [--count] [--engagement] [--out PATH] [pool]

  --count       print how many posts match this week, then exit. Returns no
                posts, so it is not billed per post. Worth running first.
  --engagement  rank by likes + reposts + replies + quotes instead of likes.
  --out PATH    where to save the run (default: x_posts_<timestamp>.json).
  pool          how many posts to fetch and rank (default 100, ~$0.005 each).
"""


def _pct(part: int, whole: int) -> str:
    """Percentage that stays informative when it is tiny.

    A pool of 100 against 104,220 matches is 0.096%, which "%.0f%%" renders as
    "0%" - a number that reads like a broken calculation rather than a fact about
    coverage.
    """
    if not whole:
        return "n/a"
    if not part:
        return "0%"
    p = 100.0 * part / whole
    if p >= 10:
        return "%.0f%%" % p
    if p >= 1:
        return "%.1f%%" % p
    if p >= 0.01:
        return "%.2f%%" % p
    return "<0.01%"


def _coverage_note(ranked: int, total: int) -> str:
    """What the week's volume says about the list we just printed.

    `ranked` is how many posts actually came back, not how many were asked for -
    the API can return fewer, and the claim has to match what was really seen.
    """
    if ranked >= total:
        return ("ranked every one of the %s posts matching in the last 7 days - "
                "so this really is the top 10" % "{:,}".format(total))
    return ("ranked %d of the %s posts matching in the last 7 days (%s), picked by "
            "X's relevance ranking, which favours engagement - so these are notable "
            "posts, not the week's definitive top 10"
            % (ranked, "{:,}".format(total), _pct(ranked, total)))


def save_run(path: str, posts: list[dict], metric: str, pool: int,
             total: int | None, query: str = VACCINE_QUERY, days: int = 7) -> str:
    """Write the ranked pool plus the metadata describing how it was gathered.

    The metadata is the point: a bare list of posts a month from now says nothing
    about which query found it, how much of the week it covers, or what "top" was
    measured on. `posts` stay in the `_normalise` shape, so `XPost.from_fetch`
    accepts them straight back out of the file.
    """
    run = {
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query": query,
        "window_days": days,
        "window_start": _window_start(days),
        "metric": metric,
        "sort_order": "relevancy",
        "pool_requested": pool,
        "pool_returned": len(posts),
        "total_matching": total,
        "coverage": _pct(len(posts), total) if total else None,
        "coverage_note": _coverage_note(len(posts), total) if total else None,
        "posts": posts,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(run, fh, ensure_ascii=False, indent=2)
    return path


def _default_out() -> str:
    """A timestamped filename that never lands on an existing file.

    The stamp is per-second, so two runs in the same second would collide - and
    each of these files is a run someone was billed for, so silently overwriting
    one is worse than an ugly suffix.
    """
    base = datetime.now(timezone.utc).strftime("x_posts_%Y%m%d-%H%M%S")
    path, n = base + ".json", 2
    while os.path.exists(path):
        path, n = "%s-%d.json" % (base, n), n + 1
    return path


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    if "-h" in argv or "--help" in argv:
        print(USAGE)
        return 0

    count_only = "--count" in argv
    metric = "engagement" if "--engagement" in argv else "likes"

    out = None
    if "--out" in argv:
        k = argv.index("--out")
        if k + 1 >= len(argv):
            print(USAGE, file=sys.stderr)
            return 2
        out = argv[k + 1]
        argv = argv[:k] + argv[k + 2:]

    positional = [a for a in argv if not a.startswith("-")]
    try:
        pool = int(positional[0]) if positional else MAX_PAGE
    except ValueError:
        print(USAGE, file=sys.stderr)
        return 2

    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    except ImportError:
        pass

    # Not billed per post, so always worth asking: this is what tells us how much
    # of the week the list below actually speaks for.
    total = None
    try:
        total = count_recent()
    except XAPIError as e:
        if count_only:
            print("error: %s" % e, file=sys.stderr)
            return 1
        print("warning: could not count the week's posts: %s" % e, file=sys.stderr)

    if count_only:
        print("%s posts match in the last 7 days." % "{:,}".format(total))
        if total:
            print("A pool of %d would cover %s of them."
                  % (pool, _pct(min(pool, total), total)))
        return 0

    try:
        ranked = rank_posts(search_recent(pool=pool), metric)
    except XAPIError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1

    if not ranked:
        print("No matching posts in the last 7 days.", file=sys.stderr)
        return 1

    print("10 notable vaccine posts from the last 7 days, by %s:" % metric,
          file=sys.stderr)
    for n, p in enumerate(ranked[:10], 1):
        present, score = _score(p, metric)
        print("%2d. %-16s %9s %-10s  %s" % (
            n, "@" + (p["author_handle"] or "?"),
            "{:,}".format(score) if present else "n/a", metric,
            (p["text"] or "").replace("\n", " ")[:60]))

    if total:
        print("\n(%s)" % _coverage_note(len(ranked), total), file=sys.stderr)
    else:
        print("\n(ranked a pool of %d posts)" % pool, file=sys.stderr)

    # Save every post we paid for, not just the ten shown.
    path = save_run(out or _default_out(), ranked, metric, pool, total)
    print("saved %d posts + run metadata to %s" % (len(ranked), path),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
