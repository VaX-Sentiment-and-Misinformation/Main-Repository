from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from x_post_fetcher import InvalidPostURL, PostUnavailable, fetch_post

load_dotenv()

app = FastAPI()

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


@app.get("/")
def health_check():
    return {"status": "healthy", "message": "FastAPI is running"}


# Defined with `def`, not `async def`: fetch_post uses blocking urllib, so
# FastAPI runs it in a threadpool instead of stalling the event loop.
@app.post("/api/post")
def get_post(payload: PostRequest):
    """Fetch a single public X post from its URL."""
    try:
        return fetch_post(payload.url)
    except InvalidPostURL as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PostUnavailable as e:
        raise HTTPException(
            status_code=404,
            detail="Could not fetch that post. It may be deleted, private, "
                   "or the link may be wrong.",
        ) from e
