"""Aggregate model-labelled vaccine posts into sentiment distributions over time and by disease.

Reads the output of predict_historical_sentiment.py. Output feeds the Trends page.

Three views:
- monthly: by the scrape month that returned each post. The scrapes had no date
  filter, so a post counts in every month it came back in, whatever its
  created_at. This is a per-scrape-run series, not when posts were written.
- daily / quarterly: by created_at, over unique posts in the scrape window. The
  final week is dense (the latest posts), while everything earlier is a thin
  set of the most-engaged posts, so they are split into the last week day by
  day and everything before it quarter by quarter.

Usage (from repo root):
    python3 backend/scripts/build_sentiment_trend.py
"""

import csv
import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "data/sentiment/historical_posts_sentiment.csv"
OUTPUT = REPO / "frontend/src/data/sentimentTrend.json"

SENTIMENTS = ("negative", "neutral", "positive")
# Buckets with fewer posts than this are shown as gaps rather than plotted,
# since a handful of posts gives a misleading distribution.
MIN_BUCKET_POSTS = 30
RECENT_DAYS = 7

# Disease tags assigned by the scraper. A post tagged with several diseases
# counts towards each; untagged posts count only towards "all".
DISEASES = [
    ("covid19", "COVID-19"),
    ("mmr", "MMR"),
    ("hpv", "HPV"),
    ("polio", "Polio"),
    ("hepatitis_b", "Hepatitis B"),
    ("hepatitis_a", "Hepatitis A"),
    ("chickenpox", "Chickenpox"),
    ("meningitis", "Meningitis"),
    ("tuberculosis", "Tuberculosis"),
]
KEYS = ["all"] + [d for d, _ in DISEASES]
LABELS = {"all": "All vaccines", **dict(DISEASES)}


def quarter_of(d: date) -> tuple[int, int]:
    return d.year, (d.month - 1) // 3 + 1


def next_quarter(q: tuple[int, int]) -> tuple[int, int]:
    return (q[0] + 1, 1) if q[1] == 4 else (q[0], q[1] + 1)


def shares(counts: Counter) -> dict:
    n = sum(counts.values())
    out = {"n": n}
    if n >= MIN_BUCKET_POSTS:
        for s in SENTIMENTS:
            out[s] = round(100 * counts[s] / n, 1)
    return out


def view(posts: list[tuple[date, str, list[str]]], bucket_of, periods: list, period_id) -> dict:
    buckets = {k: {} for k in KEYS}
    totals = {k: Counter() for k in KEYS}
    for d, label, tags in posts:
        b = bucket_of(d)
        for k in ["all", *tags]:
            buckets[k].setdefault(b, Counter())[label] += 1
            totals[k][label] += 1
    return {
        "start": str(posts[0][0]),
        "end": str(posts[-1][0]),
        "categories": [{"id": k, "label": LABELS[k], **shares(totals[k])} for k in KEYS],
        "series": {k: [{"period": period_id(p), **shares(buckets[k].get(p, Counter()))} for p in periods] for k in KEYS},
    }


def main() -> None:
    posts, by_scrape = [], []
    with SOURCE.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["predicted_sentiment"] not in SENTIMENTS:
                continue
            tags = [d for d in row["diseases"].split(";") if d in LABELS]
            posts.append((datetime.fromisoformat(row["created_at"]).date(), row["predicted_sentiment"], tags))
            for month in row["scrape_months"].split(";"):
                by_scrape.append((month, row["predicted_sentiment"], tags))
    by_scrape.sort()
    scrape_months = sorted({m for m, _, _ in by_scrape})

    # Date-based views only cover posts written within the scrape window
    window_start = date.fromisoformat(f"{scrape_months[0]}-01")
    posts = sorted(p for p in posts if p[0] >= window_start)

    recent_start = posts[-1][0] - timedelta(days=RECENT_DAYS - 1)
    recent = [p for p in posts if p[0] >= recent_start]
    earlier = [p for p in posts if p[0] < recent_start]

    days = [recent_start + timedelta(days=i) for i in range(RECENT_DAYS)]
    quarters, q = [], quarter_of(earlier[0][0])
    while q <= quarter_of(earlier[-1][0]):
        quarters.append(q)
        q = next_quarter(q)

    out = {
        "source": SOURCE.name,
        "minBucketPosts": MIN_BUCKET_POSTS,
        "overall": view(posts, lambda d: None, [], str)["categories"],
        "monthly": view(by_scrape, lambda m: m, scrape_months, str),
        "daily": view(recent, lambda d: d, days, date.isoformat),
        "quarterly": view(earlier, quarter_of, quarters, lambda q: f"{q[0]}-Q{q[1]}"),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(out, indent=2) + "\n")

    print(f"-> {OUTPUT.relative_to(REPO)}  (buckets plotted when n >= {MIN_BUCKET_POSTS})")
    for name in ("monthly", "daily", "quarterly"):
        v = out[name]
        print(f"{name}: {v['start']} to {v['end']}")
        for c in v["categories"]:
            plotted = sum("negative" in b for b in v["series"][c["id"]])
            print(f"  {c['label']:<13} n={c['n']:>5}  plotted {plotted:>2}/{len(v['series'][c['id']])}")


if __name__ == "__main__":
    main()
