"""Run the sentiment model over the monthly Apify scrapes of vaccine posts on X.

Reads every apify_vax_YYYY-MM.json in the given folder, keeps one copy of each
post (the same post can come back in several monthly scrapes) along with the
scrape months it came back in, and writes one row per post with its predicted
sentiment. Posts created before the scrape window are kept, since they still
count towards the scrapes that returned them. Run build_sentiment_trend.py afterwards to refresh the
Trends page.

Usage (from repo root, with the model weights in place):
    backend/venv/bin/python backend/scripts/predict_historical_sentiment.py "<folder of apify_vax_*.json>"
"""

import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend/model_sentiment"))
from app import LABEL_MAP, MODEL_DIR, clean_text, pick_device  # noqa: E402

OUTPUT = REPO / "data/sentiment/historical_posts_sentiment.csv"
BATCH_SIZE = 32
FIELDS = [
    "id", "created_at", "scrape_months", "author_handle", "text", "diseases",
    "likes", "reposts", "replies", "quotes", "predicted_sentiment", "confidence",
]


def parse_time(created_at: str) -> datetime:
    return datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y").astimezone(timezone.utc)


def load_posts(folder: Path) -> list[dict]:
    files = sorted(folder.glob("apify_vax_*.json"))
    if not files:
        sys.exit(f"No apify_vax_*.json files in {folder}")

    posts: dict[str, dict] = {}
    seen = 0
    for f in files:
        scrape = json.loads(f.read_text(encoding="utf-8"))
        for p in scrape["posts"]:
            seen += 1
            kept = posts.setdefault(p["id"], {**p, "diseases": set(), "scrape_months": set()})
            kept["diseases"].update(p["diseases"])
            kept["scrape_months"].add(scrape["month"])

    print(f"{len(files)} files, {seen} posts, {len(posts)} unique")
    return list(posts.values())


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    posts = load_posts(Path(sys.argv[1]).expanduser())
    posts.sort(key=lambda p: parse_time(p["created_at"]))

    device = pick_device()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).to(device).eval()

    rows = []
    texts = [clean_text(p["text"]) for p in posts]
    for i in range(0, len(texts), BATCH_SIZE):
        inputs = tokenizer(texts[i:i + BATCH_SIZE], truncation=True, max_length=256, padding=True, return_tensors="pt").to(device)
        with torch.no_grad():
            probs = model(**inputs).logits.softmax(dim=-1).cpu()
        for p, prob in zip(posts[i:i + BATCH_SIZE], probs):
            pred_id = int(prob.argmax())
            rows.append({
                **{k: p[k] for k in ("id", "author_handle", "text", "likes", "reposts", "replies", "quotes")},
                "created_at": parse_time(p["created_at"]).isoformat(),
                "scrape_months": ";".join(sorted(p["scrape_months"])),
                "diseases": ";".join(sorted(p["diseases"])),
                "predicted_sentiment": LABEL_MAP[pred_id],
                "confidence": round(float(prob[pred_id]), 4),
            })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(r["predicted_sentiment"] for r in rows)
    print(f"-> {OUTPUT.relative_to(REPO)}  ({len(rows)} posts, model {MODEL_DIR.name}, {device})")
    for label in LABEL_MAP.values():
        print(f"  {label:<9} {counts[label]:>5}  {100 * counts[label] / len(rows):.1f}%")


if __name__ == "__main__":
    main()
