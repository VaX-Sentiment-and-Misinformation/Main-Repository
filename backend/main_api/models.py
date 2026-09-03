"""Database tables.

One table for now: the X posts pulled in by x_post_fetcher. Sentiment and
misinformation predictions belong in their own table keyed on xpost.id, so a
post can be re-scored without rewriting the post row.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, Column, DateTime
from sqlmodel import Field, SQLModel

# Both backends return X's own format, e.g. "Tue Mar 21 20:50:14 +0000 2006".
X_TIME_FORMAT = "%a %b %d %H:%M:%S %z %Y"


def parse_x_time(value: str | None) -> datetime | None:
    """Turn X's timestamp string into a datetime, or None if it won't parse."""
    if not value:
        return None
    try:
        return datetime.strptime(value, X_TIME_FORMAT)
    except (ValueError, TypeError):
        return None


class XPost(SQLModel, table=True):
    """A fetched public X post.

    The primary key is the post's own ID, so re-submitting the same link
    updates rather than duplicates.
    """

    # Stored as text, not bigint: the fetcher returns strings, and that avoids
    # any chance of a 19-digit ID being mangled by an int conversion somewhere.
    id: str = Field(primary_key=True)
    url: str
    text: str
    # timestamptz, not plain timestamp: X returns a +0000 offset, and SQLModel's
    # default datetime mapping would silently discard it.
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), index=True)
    )
    lang: str | None = Field(default=None, index=True)

    author_id: str | None = None
    author_name: str | None = None
    author_handle: str | None = Field(default=None, index=True)
    # BigInteger throughout: a viral post's view count comfortably exceeds the
    # 2.1 billion ceiling of a Postgres INTEGER.
    author_followers: int | None = Field(default=None, sa_type=BigInteger)

    replies: int | None = Field(default=None, sa_type=BigInteger)
    reposts: int | None = Field(default=None, sa_type=BigInteger)
    likes: int | None = Field(default=None, sa_type=BigInteger)
    quotes: int | None = Field(default=None, sa_type=BigInteger)
    views: int | None = Field(default=None, sa_type=BigInteger)
    bookmarks: int | None = Field(default=None, sa_type=BigInteger)

    is_reply_to: str | None = None
    reply_to_handle: str | None = None
    is_quote: bool | None = None
    quoted_id: str | None = None
    possibly_sensitive: bool | None = None
    source_client: str | None = None

    media_count: int | None = None
    media_urls: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    has_poll: bool | None = None
    has_community_note: bool | None = None

    backend: str | None = None
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), index=True),
    )

    @classmethod
    def from_fetch(cls, payload: dict) -> "XPost":
        """Build a row from the dict x_post_fetcher.fetch_post returns."""
        return cls(
            id=str(payload["id"]),
            url=payload.get("url") or "",
            text=payload.get("text") or "",
            created_at=parse_x_time(payload.get("created_at")),
            lang=payload.get("lang"),
            author_id=payload.get("author_id"),
            author_name=payload.get("author_name"),
            author_handle=payload.get("author_handle"),
            author_followers=payload.get("author_followers"),
            replies=payload.get("replies"),
            reposts=payload.get("reposts"),
            likes=payload.get("likes"),
            quotes=payload.get("quotes"),
            views=payload.get("views"),
            bookmarks=payload.get("bookmarks"),
            is_reply_to=payload.get("is_reply_to"),
            reply_to_handle=payload.get("reply_to_handle"),
            is_quote=payload.get("is_quote"),
            quoted_id=payload.get("quoted_id"),
            possibly_sensitive=payload.get("possibly_sensitive"),
            source_client=payload.get("source_client"),
            media_count=payload.get("media_count"),
            media_urls=payload.get("media_urls") or [],
            has_poll=payload.get("has_poll"),
            has_community_note=payload.get("has_community_note"),
            # `_backend` is leading-underscore in the fetcher's dict, which
            # SQLModel would treat as private, so it lands here as `backend`.
            backend=payload.get("_backend"),
        )
