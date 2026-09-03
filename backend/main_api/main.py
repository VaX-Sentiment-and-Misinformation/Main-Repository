from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Must run before database.py is imported, since that reads DATABASE_URL at
# import time to build the engine.
load_dotenv()

from fastapi import Depends, FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from database import get_session, init_db  # noqa: E402
from models import XPost  # noqa: E402
from x_post_fetcher import InvalidPostURL, PostUnavailable, fetch_post, parse_post_url  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

# Allow Next.js frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PostRequest(BaseModel):
    url: str
    # Engagement counts go stale, so allow the caller to force a re-fetch of a
    # post that is already stored.
    refresh: bool = False


@app.get("/")
def health_check():
    return {"status": "healthy", "message": "FastAPI is running"}


# Defined with `def`, not `async def`: fetch_post uses blocking urllib and the
# psycopg2 driver is blocking too, so FastAPI runs this in a threadpool instead
# of stalling the event loop.
@app.post("/api/post")
def get_post(payload: PostRequest, session: Session = Depends(get_session)):
    """Fetch a public X post from its URL, storing it on first sight."""
    try:
        post_id = parse_post_url(payload.url)
    except InvalidPostURL as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not payload.refresh:
        cached = session.get(XPost, post_id)
        if cached:
            return {**cached.model_dump(), "_cached": True}

    try:
        fetched = fetch_post(payload.url)
    except PostUnavailable as e:
        raise HTTPException(
            status_code=404,
            detail="Could not fetch that post. It may be deleted, private, "
                   "or the link may be wrong.",
        ) from e

    row = XPost.from_fetch(fetched)
    # merge() rather than add(): on a refresh the row already exists, and this
    # updates it in place instead of raising a duplicate-key error.
    row = session.merge(row)
    session.commit()
    session.refresh(row)
    return {**row.model_dump(), "_cached": False}


@app.get("/api/posts")
def list_posts(limit: int = 50, session: Session = Depends(get_session)):
    """Most recently fetched posts, for the results view."""
    limit = max(1, min(limit, 200))
    rows = session.exec(
        select(XPost).order_by(XPost.fetched_at.desc()).limit(limit)
    ).all()
    return rows
