"""Database engine and session handling.

Targets Postgres hosted on Supabase. See backend/.env.example for how to get
the connection string — the short version is that on the free tier you want the
**Session pooler** string, not the direct connection, because direct connections
resolve to IPv6 only unless you pay for the IPv4 add-on.
"""

import os
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

# Imported for its side effect: the table classes must be registered on
# SQLModel.metadata before init_db() calls create_all().
from models import XPost  # noqa: F401


class DatabaseNotConfigured(RuntimeError):
    """DATABASE_URL is missing or unusable."""


def normalise_url(url: str) -> str:
    """Make a pasted connection string safe for SQLAlchemy 2.x.

    Supabase (and Heroku, and others) hand out `postgres://`, a scheme
    SQLAlchemy 2.x dropped. Rewriting it here saves a confusing
    NoSuchModuleError at import time.
    """
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def build_engine(url: str, echo: bool = False):
    """Create the engine with settings suited to a pooled Supabase connection."""
    url = normalise_url(url)
    kwargs = {"echo": echo}

    if url.startswith("postgresql"):
        kwargs.update(
            # Supavisor hangs up on idle connections, and a free-tier project
            # pauses after inactivity. Without pre_ping the first request after
            # a quiet spell fails with "SSL connection has been closed".
            pool_pre_ping=True,
            pool_recycle=300,
            # The free tier's connection allowance is small and shared with the
            # Supabase dashboard, so stay modest rather than using the default 5+10.
            pool_size=5,
            max_overflow=2,
            connect_args={"sslmode": "require", "connect_timeout": 10},
        )

    return create_engine(url, **kwargs)


def _require_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise DatabaseNotConfigured(
            "DATABASE_URL is not set. Copy backend/.env.example to backend/.env "
            "and paste your Supabase connection string into it."
        )
    return url


engine = build_engine(_require_url()) if os.getenv("DATABASE_URL") else None


def init_db() -> None:
    """Create any missing tables.

    Fine for a project this size. If the schema starts changing after there is
    data worth keeping, this is the point to bring in Alembic instead —
    create_all only ever adds tables, it never alters existing ones.
    """
    if engine is None:
        raise DatabaseNotConfigured(_require_url.__doc__ or "DATABASE_URL is not set")
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a session per request."""
    if engine is None:
        raise DatabaseNotConfigured("DATABASE_URL is not set")
    with Session(engine) as session:
        yield session
