"""Whether a claim is vaccine misinformation, straight from the misinformation model.

Sends the claim text to the misinformation model service and returns its label
and the model's confidence in each of not_misinformation / misinformation. If
the claim is an X post URL, the post is fetched first and its text is what gets
analysed.

A local LLM (via Ollama) can then explain the label in plain language. That is
a separate endpoint because it takes ~10s, so the page can show the score first.
"""

import logging
import os
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from sentiment import fetch_post_text
from validators import MAX_TEXT_LENGTH, InputValidationError, classify_input

log = logging.getLogger(__name__)

MISINFO_MODEL_URL = os.getenv("MISINFO_MODEL_URL", "http://localhost:8002/predict")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# Prompt from the team's trial.py, so explanations match the ones tested there
EXPLANATION_PROMPT = """
You are providing a short explanation for the result of a
vaccine misinformation classifier.

STATEMENT:
"{statement}"

CLASSIFICATION:
{classification}

The classification has already been determined by another
machine learning model.

Your task is to explain why the statement fits this
classification.

Rules:

1. Do NOT change the classification.
2. Do NOT provide another classification.
3. Base the explanation on established scientific evidence.
4. Do NOT invent studies, statistics, organisations, or sources.
5. If the statement is MISINFORMATION, briefly explain what is
   scientifically inaccurate or unsupported.
6. If the statement is NOT_MISINFORMATION, briefly explain why
   it is consistent with established evidence or does not make
   a false vaccine claim.
7. Use simple language.
8. Keep the explanation to 1-2 sentences.
9. Return ONLY the explanation.

Explanation:
"""

router = APIRouter()


async def predict(text: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(MISINFO_MODEL_URL, json={"texts": [text]})
            res.raise_for_status()
        prediction = res.json()["predictions"][0]
        return {"label": prediction["label"], "scores": prediction["scores"]}
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as err:
        log.warning("Misinformation model unavailable at %s (%s)", MISINFO_MODEL_URL, err)
        raise HTTPException(status_code=503, detail="Misinformation model unavailable") from err


@router.get("/analyse/misinformation")
async def analyse_misinformation(q: str = Query(min_length=1)):
    try:
        claim = classify_input(q)
    except InputValidationError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err

    post = await fetch_post_text(q) if claim["type"] == "url" else None
    text = post["text"] if post else q

    return {"query": q, "text": text, "post": post, **await predict(text)}


class ExplanationRequest(BaseModel):
    # The text the model scored (from /analyse/misinformation) and the label it gave
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    label: Literal["misinformation", "not_misinformation"]


@router.post("/analyse/misinformation/explanation")
async def explain_misinformation(payload: ExplanationRequest):
    prompt = EXPLANATION_PROMPT.format(statement=payload.text, classification=payload.label.upper())
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1},
            })
            res.raise_for_status()
        explanation = res.json()["response"].strip()
    except (httpx.HTTPError, KeyError, ValueError) as err:
        log.warning("Explanation model unavailable at %s (%s)", OLLAMA_URL, err)
        raise HTTPException(status_code=503, detail="Explanation model unavailable") from err
    if not explanation:
        raise HTTPException(status_code=503, detail="Explanation model returned nothing")
    return {"explanation": explanation}
