"""Pick the most popular recent vaccine posts for the "Trending posts" cards on the home and Trends pages.

Reads an Apify scrape (apify_vax_*.json from backend/main_api/apify - normally
the output of fetch_week, but a monthly file works too), keeps the posts from its
last 7 days, and takes the most-engaged ones (likes + reposts + replies + quotes,
one post per author). Each is run through the sentiment and misinformation
models, the same as the result page would score it.

Usage (from repo root, with both models' weights in place):
    backend/venv/bin/python backend/scripts/build_trending_posts.py <apify_vax_*.json>
"""

import html
import importlib.util
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend/main_api"))
from apify.normalise import engagement  # noqa: E402

OUTPUT = REPO / "frontend/src/data/trendingPosts.json"

WINDOW = timedelta(days=7)
# The Trends page shows them all, the home page the first few
CARDS = 9
QUOTE_LENGTH = 180


def load_service(name: str, folder: str):
    """A model service's app.py. Both services name it app.py, so import by path."""
    spec = importlib.util.spec_from_file_location(name, REPO / folder / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def predict(service, texts: list[str]) -> list[dict]:
    """{label: probability} per text, as the service's /predict would score it."""
    device = service.pick_device()
    tokenizer = AutoTokenizer.from_pretrained(service.MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(service.MODEL_DIR).to(device).eval()
    inputs = tokenizer(
        [service.clean_text(t) for t in texts], truncation=True, max_length=256, padding=True, return_tensors="pt"
    ).to(device)
    with torch.no_grad():
        probs = model(**inputs).logits.softmax(dim=-1).cpu()
    return [{service.LABEL_MAP[i]: float(p[i]) for i in service.LABEL_MAP} for p in probs]


def parse_time(created_at: str) -> datetime:
    return datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y").astimezone(timezone.utc)


def quote(text: str) -> str:
    """The post's text without links, cut at a word boundary to fit the card."""
    text = re.sub(r"https?://\S+", " ", html.unescape(text))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > QUOTE_LENGTH:
        text = text[:QUOTE_LENGTH].rsplit(" ", 1)[0].rstrip(",.;:-") + "..."
    return text


def compact(n: int) -> str:
    """12400 -> "12.4k", as the rest of the site shows counts."""
    for size, suffix in ((1_000_000, "M"), (1_000, "k")):
        if n >= size:
            return f"{n / size:.1f}".rstrip("0").rstrip(".") + suffix
    return str(n)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    source = Path(sys.argv[1]).expanduser()
    posts = json.loads(source.read_text(encoding="utf-8"))["posts"]
    for p in posts:
        p["created_at"] = parse_time(p["created_at"])

    end = max(p["created_at"] for p in posts)
    start = end - WINDOW
    week = sorted((p for p in posts if p["created_at"] > start), key=engagement, reverse=True)

    # One post per author, so one prolific account can't fill every card
    top, authors = [], set()
    for p in week:
        if p["author_handle"] not in authors:
            top.append(p)
            authors.add(p["author_handle"])
        if len(top) == CARDS:
            break

    texts = [p["text"] for p in top]
    sentiments = predict(load_service("sentiment_app", "backend/model_sentiment"), texts)
    misinfo = predict(load_service("misinfo_app", "backend/model_misinformation"), texts)

    cards = []
    for p, sentiment, mis in zip(top, sentiments, misinfo):
        pct = round(100 * mis["misinformation"])
        cards.append({
            "sentiment": max(sentiment, key=sentiment.get),
            "author": p["author_name"] or p["author_handle"],
            "handle": p["author_handle"],
            "body": quote(p["text"]),
            "postUrl": p["url"],
            "likes": f"{compact(p['likes'] or 0)} likes",
            "score": f"{pct}%",
            "pct": pct,
        })

    out = {
        "source": source.name,
        "start": start.date().isoformat(),
        "end": end.date().isoformat(),
        "posts": cards,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")

    print(f"-> {OUTPUT.relative_to(REPO)}  (top {len(cards)} of {len(week)} posts, {out['start']} to {out['end']})")
    for c in cards:
        print(f"  @{c['handle']:<16} {c['likes']:>12}  {c['sentiment']:<8}  misinfo {c['score']:>4}")


if __name__ == "__main__":
    main()
