"""Map an Apify tweet-scraper item onto this project's post dict.

Three sources already emit the same flat shape - x_post_fetcher.fetch_post,
x-scraper.py and x_api_search._normalise - and XPost.from_fetch consumes it. This
makes Apify the fourth, so its output loads into Postgres with no model changes.

The Actor's `createdAt` is X's legacy format ("Fri Nov 24 17:49:36 +0000 2023"),
which is exactly what models.parse_x_time reads as its first format. That is luck
worth knowing about: the official v2 API returns ISO 8601 instead, and parse_x_time
handles both.
"""

__all__ = ["normalise", "engagement"]

BACKEND = "apify-tweet-scraper"


def normalise(item: dict) -> dict:
    """One Actor dataset item -> the shape XPost.from_fetch expects."""
    author = item.get("author") or {}

    media_urls = _media_urls(item)

    return {
        "id": str(item.get("id")) if item.get("id") is not None else None,
        "url": item.get("url") or item.get("twitterUrl"),
        # Legacy X format; models.parse_x_time reads it directly.
        "created_at": item.get("createdAt"),
        "created_timestamp": None,
        "text": item.get("text"),
        "lang": item.get("lang"),

        "author_name": author.get("name"),
        "author_handle": author.get("userName"),
        "author_id": str(author["id"]) if author.get("id") is not None else None,
        "author_followers": author.get("followers"),

        "replies": item.get("replyCount"),
        "reposts": item.get("retweetCount"),
        "likes": item.get("likeCount"),
        "quotes": item.get("quoteCount"),
        # The Actor does not expose a view count at all - not zero, absent. Left
        # explicitly None so nothing downstream reads a 0 as "nobody saw this".
        # Rank on likes/reposts/replies/quotes instead.
        "views": None,
        "bookmarks": item.get("bookmarkCount"),

        "is_reply_to": _str_or_none(item.get("inReplyToId")),
        "reply_to_handle": item.get("inReplyToUsername"),
        "is_quote": item.get("isQuote"),
        "quoted_id": _str_or_none(item.get("quoteId")),
        "possibly_sensitive": item.get("possiblySensitive"),
        # A small win over the official path: X's v2 API dropped `source`, but the
        # Actor still reports the posting client.
        "source_client": item.get("source"),

        "media_count": len(media_urls),
        "media_urls": media_urls,
        "has_poll": bool(item.get("card")) or None,
        "has_community_note": None,

        "_backend": BACKEND,
    }


def _str_or_none(value):
    return str(value) if value is not None else None


def _media_urls(item: dict) -> list[str]:
    """Best-effort media extraction.

    The Actor's media layout is not pinned down in its published sample, so this
    reads the usual X entity shapes and returns [] rather than guessing wrongly.
    """
    urls: list[str] = []
    entities = item.get("extendedEntities") or item.get("entities") or {}
    for media in (entities.get("media") or []):
        url = media.get("media_url_https") or media.get("media_url") or media.get("url")
        if url:
            urls.append(url)
    return urls


def engagement(post: dict) -> int:
    """Total interactions on a normalised post: likes + reposts + replies + quotes.

    Deliberately excludes views, which this backend never supplies, and bookmarks,
    which are a private signal rather than an interaction with the post.
    """
    return sum(post.get(k) or 0 for k in ("likes", "reposts", "replies", "quotes"))
