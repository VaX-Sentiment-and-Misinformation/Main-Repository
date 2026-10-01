"""Sentiment of a claim towards vaccination, straight from the sentiment model.

Sends the claim text to the sentiment model service and returns its label and
the model's confidence in each of negative / neutral / positive.
"""

import logging
import os

import httpx
from fastapi import APIRouter, HTTPException, Query

from validators import InputValidationError, classify_input

log = logging.getLogger(__name__)

SENTIMENT_MODEL_URL = os.getenv("SENTIMENT_MODEL_URL", "http://localhost:8001/predict")

router = APIRouter()


@router.get("/analyse/sentiment")
async def analyse_sentiment(q: str = Query(min_length=1)):
    try:
        claim = classify_input(q)
    except InputValidationError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    if claim["type"] == "url":
        # Fetching a post's text from its URL isn't supported yet
        raise HTTPException(status_code=422, detail="Post URLs aren't supported yet; paste the post's text instead.")

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(SENTIMENT_MODEL_URL, json={"texts": [q]})
            res.raise_for_status()
        prediction = res.json()["predictions"][0]
        label, scores = prediction["label"], prediction["scores"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as err:
        log.warning("Sentiment model unavailable at %s (%s)", SENTIMENT_MODEL_URL, err)
        raise HTTPException(status_code=503, detail="Sentiment model unavailable") from err

    return {"query": q, "label": label, "scores": scores}
