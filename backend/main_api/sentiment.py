"""Sentiment of a claim towards vaccination, straight from the sentiment model.

Sends the claim text to the sentiment model service and returns its label and
the model's confidence in each of negative / neutral / positive. If the claim
is an X post URL, the post is fetched first and its text is what gets analysed.
"""

import logging
import os

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from validators import InputValidationError, classify_input
from x_post_fetcher import InvalidPostURL, PostUnavailable, fetch_post

log = logging.getLogger(__name__)

SENTIMENT_MODEL_URL = os.getenv("SENTIMENT_MODEL_URL", "http://localhost:8001/predict")

router = APIRouter()


async def fetch_post_text(url: str) -> dict:
    # fetch_post uses blocking urllib, so keep it off the event loop. Fewer
    # retries and a shorter timeout than its defaults, since a user is waiting.
    try:
        post = await run_in_threadpool(fetch_post, url, retries=1, timeout=10)
    except InvalidPostURL as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    except PostUnavailable as err:
        log.info("Post fetch failed: %s", err)
        raise HTTPException(
            status_code=404,
            detail="Couldn't fetch that post. It may be deleted or private, or the link may be wrong.",
        ) from err
    if not (post.get("text") or "").strip():
        raise HTTPException(status_code=422, detail="That post has no text to analyse.")
    return post


async def predict(text: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(SENTIMENT_MODEL_URL, json={"texts": [text]})
            res.raise_for_status()
        prediction = res.json()["predictions"][0]
        return {"label": prediction["label"], "scores": prediction["scores"]}
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as err:
        log.warning("Sentiment model unavailable at %s (%s)", SENTIMENT_MODEL_URL, err)
        raise HTTPException(status_code=503, detail="Sentiment model unavailable") from err


@router.get("/analyse/sentiment")
async def analyse_sentiment(q: str = Query(min_length=1)):
    try:
        claim = classify_input(q)
    except InputValidationError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err

    post = await fetch_post_text(q) if claim["type"] == "url" else None
    text = post["text"] if post else q

    return {"query": q, "text": text, "post": post, **await predict(text)}
