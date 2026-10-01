#!/usr/bin/env python3
"""
x_post_fetcher.py - fetch a single public X (Twitter) post from its URL.

Extracted from x-scraper.py, which is a bulk/CLI tool. This module is the
single-post path only, importable and stdlib-only:

    from x_post_fetcher import fetch_post, PostUnavailable

    post = fetch_post("https://x.com/jack/status/20")
    print(post["author_handle"], post["text"])

Backends are tried in order:
  1. fxtwitter   - api.fxtwitter.com/2/status/{id}  (public, ~1000 req/min per IP)
  2. syndication - cdn.syndication.twimg.com/tweet-result  (X's own embed endpoint)

No API key, no login. Python 3.8+.
"""

import json
import math
import random
import re
import sys
import time
import urllib.error
import urllib.request

__all__ = ["fetch_post", "parse_post_url", "PostUnavailable", "InvalidPostURL"]

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
FX = "https://api.fxtwitter.com/2/status/{id}"
SYND = "https://cdn.syndication.twimg.com/tweet-result?id={id}&token={token}&lang=en"

# x.com, twitter.com, mobile.twitter.com, vxtwitter, fxtwitter, nitter mirrors -
# all share the /{handle}/status/{id} shape, so match on that rather than host.
STATUS_RE = re.compile(r"status(?:es)?/(\d+)")
ID_RE = re.compile(r"(\d{5,25})")

DEFAULT_BACKENDS = ("fxtwitter", "syndication")


class InvalidPostURL(ValueError):
    """The input had no post ID in it."""


class PostUnavailable(LookupError):
    """Every backend was reached but none could return the post.

    Deleted, suspended, protected, or simply never existed. `errors` holds one
    message per backend so the specific reason isn't masked by the fallback's
    generic one.
    """

    def __init__(self, post_id, errors):
        self.post_id = post_id
        self.errors = list(errors)
        super().__init__("post %s unavailable: %s" % (post_id, " | ".join(self.errors)))


# ---------- URL parsing ----------

def parse_post_url(raw):
    """Pull the post ID out of an X/Twitter URL (or accept a bare ID).

    Handles query strings and trailing paths (?s=20, /photo/1), any of the
    mirror domains, and bare numeric IDs. Raises InvalidPostURL on junk.
    """
    if raw is None or not str(raw).strip():
        raise InvalidPostURL("empty input")
    raw = str(raw).strip()

    m = STATUS_RE.search(raw)
    if m:
        return m.group(1)
    if raw.isdigit():          # bare ID, any length (the first ever post is just "20")
        return raw
    m = ID_RE.search(raw)      # otherwise dig one out of surrounding junk
    if m:
        return m.group(1)
    raise InvalidPostURL("no post ID found in %r" % raw)


# ---------- transport ----------

def _base36(x):
    """Port of JS Number.prototype.toString(36) for positive floats."""
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    ip, frac = int(x), x - int(x)
    if ip == 0:
        head = "0"
    else:
        head = ""
        while ip:
            head = digits[ip % 36] + head
            ip //= 36
    if frac <= 0:
        return head
    tail = ""
    for _ in range(20):
        frac *= 36
        d = int(frac)
        tail += digits[d]
        frac -= d
        if frac == 0:
            break
    return head + "." + tail


def _synd_token(post_id):
    """Same token derivation X's own embed widget uses."""
    return re.sub(r"(0+|\.)", "", _base36((int(post_id) / 1e15) * math.pi))


def _get_json(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# ---------- backends ----------

def _via_fxtwitter(post_id, timeout):
    data = _get_json(FX.format(id=post_id), timeout)
    if data.get("code") != 200:
        raise LookupError(data.get("message") or "code %s" % data.get("code"))
    s = data.get("status") or {}
    if s.get("type") == "tombstone":
        raise LookupError(s.get("reason") or "unavailable")

    a = s.get("author") or {}
    media = (s.get("media") or {}).get("all") or []
    reply = s.get("replying_to") or {}

    return {
        "id": s.get("id"),
        "url": s.get("url"),
        "created_at": s.get("created_at"),
        "created_timestamp": s.get("created_timestamp"),
        "text": s.get("text"),
        "lang": s.get("lang"),
        "author_name": a.get("name"),
        "author_handle": a.get("screen_name"),
        "author_id": a.get("id"),
        "author_followers": a.get("followers"),
        "replies": s.get("replies"),
        "reposts": s.get("reposts"),
        "likes": s.get("likes"),
        "quotes": s.get("quotes"),
        "views": s.get("views"),
        "bookmarks": s.get("bookmarks"),
        "is_reply_to": reply.get("status"),
        "reply_to_handle": reply.get("screen_name"),
        "is_quote": bool(s.get("quote")),
        "quoted_id": (s.get("quote") or {}).get("id"),
        "possibly_sensitive": s.get("possibly_sensitive"),
        "source_client": s.get("source"),
        "media_count": len(media),
        "media_urls": [m.get("url") for m in media if m.get("url")],
        "has_poll": bool(s.get("poll")),
        "has_community_note": bool(s.get("community_note")),
        "_backend": "fxtwitter",
    }


def _via_syndication(post_id, timeout):
    data = _get_json(SYND.format(id=post_id, token=_synd_token(post_id)), timeout)
    if not data or "text" not in data:
        raise LookupError("empty syndication response")

    u = data.get("user") or {}
    media = data.get("mediaDetails") or []
    return {
        "id": data.get("id_str") or str(post_id),
        "url": "https://x.com/%s/status/%s" % (u.get("screen_name", "i"), post_id),
        "created_at": data.get("created_at"),
        "created_timestamp": None,
        "text": data.get("text"),
        "lang": data.get("lang"),
        "author_name": u.get("name"),
        "author_handle": u.get("screen_name"),
        "author_id": u.get("id_str"),
        "author_followers": None,
        "replies": data.get("conversation_count"),
        "reposts": None,
        "likes": data.get("favorite_count"),
        "quotes": None,
        "views": None,
        "bookmarks": None,
        "is_reply_to": data.get("in_reply_to_status_id_str"),
        "reply_to_handle": data.get("in_reply_to_screen_name"),
        "is_quote": bool(data.get("quoted_tweet")),
        "quoted_id": (data.get("quoted_tweet") or {}).get("id_str"),
        "possibly_sensitive": data.get("possibly_sensitive"),
        "source_client": None,
        "media_count": len(media),
        "media_urls": [m.get("media_url_https") for m in media if m.get("media_url_https")],
        "has_poll": bool(data.get("card")),
        "has_community_note": None,
        "_backend": "syndication",
    }


BACKENDS = {"fxtwitter": _via_fxtwitter, "syndication": _via_syndication}


# ---------- public API ----------

def fetch_post(url, backends=DEFAULT_BACKENDS, retries=3, timeout=20):
    """Fetch one public X post given its URL (or bare ID). Returns a dict.

    Tries each backend in order, retrying transient failures with exponential
    backoff. Permanent HTTP codes (400/401/403/404) and a backend that answers
    "not available" move straight on to the next backend.

    Raises InvalidPostURL if no ID can be parsed, PostUnavailable if every
    backend failed.
    """
    post_id = parse_post_url(url)
    errors = []

    for name in backends:
        fn = BACKENDS[name]
        err = None
        for attempt in range(retries + 1):
            try:
                return fn(post_id, timeout)
            except urllib.error.HTTPError as e:
                err = "%s HTTP %s" % (name, e.code)
                if e.code in (400, 401, 403, 404):
                    break  # permanent for this backend, move on
                time.sleep(min(30, (2 ** attempt) + random.random()))
            except LookupError as e:
                err = "%s: %s" % (name, e)
                break  # backend answered, post genuinely isn't available
            except Exception as e:
                err = "%s: %s" % (name, e)
                time.sleep(min(30, (2 ** attempt) + random.random()))
        if err:
            errors.append(err)

    raise PostUnavailable(post_id, errors)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python x_post_fetcher.py <x.com post URL or ID>", file=sys.stderr)
        return 2
    try:
        post = fetch_post(argv[0])
    except (InvalidPostURL, PostUnavailable) as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    print(json.dumps(post, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
