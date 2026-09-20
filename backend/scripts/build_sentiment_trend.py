"""Aggregate labelled vaccine tweets into sentiment distributions over time and by vaccine.

Tweet timestamps are decoded from the Twitter snowflake IDs, so no API call is
needed. Output feeds the Trends page chart.

Usage (from repo root):
    python3 backend/scripts/build_sentiment_trend.py
"""

import csv
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "data/misinformation/Labeled/misinfo_sentiment_predictions.csv"
OUTPUT = REPO / "frontend/src/data/sentimentTrend.json"

TWITTER_EPOCH_MS = 1288834974657
SENTIMENTS = ("negative", "neutral", "positive")
# Buckets with fewer tweets than this are shown as gaps rather than plotted,
# since a handful of tweets gives a misleading distribution.
MIN_BUCKET_TWEETS = 50

# Keyword categories, matched case-insensitively. A tweet naming several brands
# counts towards each; one naming none falls into "unnamed".
# The dataset is COVID-era, so brands are COVID-19 vaccines. Flu is deliberately
# not a category: most flu mentions compare it to the COVID vaccine.
CATEGORIES = [
    ("pfizer", "Pfizer", r"pfizer|biontech|comirnaty"),
    ("moderna", "Moderna", r"moderna"),
    ("astrazeneca", "AstraZeneca", r"astra ?zeneca|oxford|covishield"),
    ("jnj", "J&J", r"johnson|janssen|\bj ?& ?j\b|\bjnj\b"),
    ("other", "Other brands", r"sinovac|coronavac|sinopharm|covaxin|sputnik|novavax"),
]
UNNAMED = ("unnamed", "No brand named")
PATTERNS = {cid: re.compile(p, re.IGNORECASE) for cid, _, p in CATEGORIES}


def tweet_time(tweet_id: str) -> datetime:
    ms = (int(tweet_id) >> 22) + TWITTER_EPOCH_MS
    return datetime.fromtimestamp(ms / 1000, timezone.utc)


def week_start(d: datetime) -> datetime:
    d = d.replace(hour=0, minute=0, second=0, microsecond=0)
    return d - timedelta(days=d.weekday())


def month_start(d: datetime) -> datetime:
    return d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def next_month(d: datetime) -> datetime:
    return d.replace(year=d.year + d.month // 12, month=d.month % 12 + 1)


def categories_of(text: str) -> list[str]:
    hits = [cid for cid, pattern in PATTERNS.items() if pattern.search(text)]
    return hits or [UNNAMED[0]]


def shares(counts: Counter) -> dict:
    n = sum(counts.values())
    out = {"n": n}
    if n >= MIN_BUCKET_TWEETS:
        for s in SENTIMENTS:
            out[s] = round(100 * counts[s] / n, 1)
    return out


def series(buckets: dict[datetime, Counter], periods: list[datetime]) -> list[dict]:
    return [{"period": p.date().isoformat(), **shares(buckets.get(p, Counter()))} for p in periods]


def main() -> None:
    keys = ["all"] + [cid for cid, _, _ in CATEGORIES] + [UNNAMED[0]]
    weekly = {k: {} for k in keys}
    monthly = {k: {} for k in keys}
    totals = {k: Counter() for k in keys}

    with SOURCE.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            label = row["predicted_sentiment"].strip().lower()
            if label not in SENTIMENTS:
                continue
            t = tweet_time(row["id"])
            wk, mo = week_start(t), month_start(t)
            for k in ["all", *categories_of(row["text"])]:
                weekly[k].setdefault(wk, Counter())[label] += 1
                monthly[k].setdefault(mo, Counter())[label] += 1
                totals[k][label] += 1

    # Every period between first and last is emitted so collection gaps stay
    # visible, and all categories share one axis.
    weeks, wk = [], min(weekly["all"])
    while wk <= max(weekly["all"]):
        weeks.append(wk)
        wk += timedelta(weeks=1)
    months, mo = [], min(monthly["all"])
    while mo <= max(monthly["all"]):
        months.append(mo)
        mo = next_month(mo)

    labels = {"all": "All vaccines", **{cid: name for cid, name, _ in CATEGORIES}, UNNAMED[0]: UNNAMED[1]}
    out = {
        "source": SOURCE.name,
        "minBucketTweets": MIN_BUCKET_TWEETS,
        "categories": [{"id": k, "label": labels[k], **shares(totals[k])} for k in keys],
        "series": {
            "weekly": {k: series(weekly[k], weeks) for k in keys},
            "monthly": {k: series(monthly[k], months) for k in keys},
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(out, indent=2) + "\n")

    print(f"-> {OUTPUT.relative_to(REPO)}  (buckets plotted when n >= {MIN_BUCKET_TWEETS})")
    for k in keys:
        pw = sum("negative" in b for b in out["series"]["weekly"][k])
        pm = sum("negative" in b for b in out["series"]["monthly"][k])
        print(f"  {labels[k]:<16} n={sum(totals[k].values()):>5}  weeks {pw:>2}/{len(weeks)}  months {pm}/{len(months)}")


if __name__ == "__main__":
    main()
