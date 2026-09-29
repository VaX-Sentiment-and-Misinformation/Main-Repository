"""Sentiment of the posts discussing a claim.

Finds tweets in the labelled dataset that match the query, sends them to the
sentiment model service, and returns the negative / neutral / positive split.
If the model service is unreachable, the stored predictions in the dataset are
used instead so the frontend still works.
"""

import csv
import logging
import math
import os
import re
from collections import Counter
from pathlib import Path

import httpx
from fastapi import APIRouter, Query

log = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parents[2]
CORPUS_PATH = Path(os.getenv(
    "SENTIMENT_CORPUS_PATH", REPO / "data/misinformation/Labeled/misinfo_sentiment_predictions.csv"
))
SENTIMENT_MODEL_URL = os.getenv("SENTIMENT_MODEL_URL", "http://localhost:8001/predict")
# The most relevant posts are sent to the model; more makes the page slower on CPU.
MAX_POSTS = 100
SENTIMENTS = ("positive", "neutral", "negative")

STOPWORDS = {
    "a", "about", "after", "all", "also", "am", "an", "and", "any", "are", "as", "at", "be", "been", "being",
    "but", "by", "can", "could", "did", "do", "does", "doing", "for", "from", "get", "got", "had", "has",
    "have", "he", "her", "him", "his", "how", "i", "if", "in", "into", "is", "it", "its", "just", "me",
    "more", "my", "no", "not", "of", "on", "once", "one", "only", "or", "our", "out", "she", "so", "some",
    "than", "that", "the", "their", "them", "then", "there", "these", "they", "this", "those", "to", "too",
    "up", "us", "very", "was", "we", "were", "what", "when", "where", "which", "who", "why", "will", "with",
    "would", "you", "your",
}
# Nearly every post in the dataset mentions these, so they say nothing about relevance.
GENERIC = {"vaccine", "vaccinate", "vaccinated", "vaccination", "vax", "covid", "covid19", "coronavirus"}


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", re.sub(r"http\S+", "", text.lower()))
    # Crude plural folding so "vaccines" matches "vaccine" and "shots" matches "shot"
    return {w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in words}


def load_corpus() -> tuple[list[dict], dict[str, float]]:
    posts = []
    with CORPUS_PATH.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            label = row["predicted_sentiment"].strip().lower()
            if label in SENTIMENTS:
                posts.append({"text": row["text"], "label": label, "tokens": tokens(row["text"])})
    df = Counter(t for p in posts for t in p["tokens"])
    idf = {t: math.log(len(posts) / n) for t, n in df.items()}
    return posts, idf


POSTS, IDF = load_corpus()


def related_posts(query: str) -> list[dict]:
    """Posts ranked by IDF-weighted keyword overlap with the query.

    A post must cover at least half of the query's total keyword weight, so a
    match on a rare word ("autism") counts but a match on a common one ("cause")
    alone does not.
    """
    keywords = {k for k in tokens(query) - STOPWORDS - GENERIC if k in IDF}
    if not keywords:
        return []
    max_score = sum(IDF[k] for k in keywords)
    scored = []
    for post in POSTS:
        score = sum(IDF[k] for k in keywords & post["tokens"])
        if score > 0 and score >= max_score / 2:
            scored.append((score, post))
    scored.sort(key=lambda sp: sp[0], reverse=True)
    return [post for _, post in scored]


def percentages(counts: Counter) -> dict[str, int]:
    """Whole-number percentages that add up to 100 (largest remainder)."""
    total = sum(counts.values())
    if not total:
        return {s: 0 for s in SENTIMENTS}
    exact = {s: 100 * counts[s] / total for s in SENTIMENTS}
    pct = {s: math.floor(v) for s, v in exact.items()}
    for s in sorted(SENTIMENTS, key=lambda s: exact[s] - pct[s], reverse=True)[:100 - sum(pct.values())]:
        pct[s] += 1
    return pct


async def classify(texts: list[str]) -> list[str] | None:
    """Labels from the model service, or None if it can't be reached."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(SENTIMENT_MODEL_URL, json={"texts": texts})
            res.raise_for_status()
        return [p["label"] for p in res.json()["predictions"]]
    except (httpx.HTTPError, KeyError, ValueError) as err:
        log.warning("Sentiment model unavailable at %s (%s); using stored predictions", SENTIMENT_MODEL_URL, err)
        return None


router = APIRouter()


@router.get("/analyse/sentiment")
async def analyse_sentiment(q: str = Query(min_length=1, max_length=4000)):
    matches = related_posts(q)
    sample = matches[:MAX_POSTS]

    labels = await classify([p["text"] for p in sample]) if sample else []
    source = "model" if sample else None
    if labels is None:
        labels = [p["label"] for p in sample]
        source = "stored"

    counts = Counter(labels)
    pct = percentages(counts)
    return {
        "query": q,
        "matched": len(matches),
        "analysed": len(sample),
        "source": source,
        "sentiment": {s: {"count": counts[s], "pct": pct[s]} for s in SENTIMENTS},
    }
