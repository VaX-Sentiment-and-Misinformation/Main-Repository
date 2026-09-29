#!/usr/bin/env python3
"""
x_historical_search.py - vaccine posts for nine diseases, sampled by quarter.

Where x_api_search.py covers the rolling 7-day window, this reaches back years via
GET /2/tweets/search/all (full-archive search). It samples evenly over time rather
than grabbing a single blob of recent posts: a run covers the last N calendar
quarters, and each disease gets the same small number of posts from every quarter,
so the resulting corpus can be compared across both disease and time.

    from x_historical_search import fetch_disease, DISEASES

    posts = fetch_disease("hpv")        # 24 posts, 3 from each of 8 quarters

Structure follows xdevplatform/samples/python/posts/search_all.py, but that sample
uses X's `xdk` SDK; this module stays stdlib-only like the rest of the backend and
borrows _get/_normalise from x_api_search.

Three things to know before running it:

1. **This endpoint needs an entitlement the default plan does not include.**
   Full-archive search requires Self-serve or Enterprise access; the pay-per-use
   default covers only the last 7 days. Until someone upgrades in the developer
   console, every call here returns 403. Use --dry-run, which touches no network,
   to review the queries in the meantime.

2. **A request bills ~10 posts even when we keep 3.** `max_results` has a floor of
   10 and billing is per post *returned*. The default run is 9 diseases x 8
   quarters = 72 requests, so roughly 720 posts billed (~$3.60) to keep 216.
   `--keep-all` keeps everything those requests returned, for the same money.

3. **Full-archive allows one request per second**, so a full run is throttled and
   takes about two minutes.

Requires X_BEARER_TOKEN in backend/.env, same as x_api_search.py.
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

from x_api_search import XAPIError, _get, _normalise, rank_posts

__all__ = ["fetch_disease", "search_all", "quarters", "save_disease",
           "DISEASES", "XAPIError"]

SEARCH_ALL_URL = "https://api.x.com/2/tweets/search/all"

# The API will not return fewer than 10 per request, and we are billed for what it
# returns - so 10 is the true cost of asking for 2.
MIN_PAGE = 10
MAX_PAGE = 500

# Full-archive is capped at 1 request/second (300 per 15 min). A little over 1s
# keeps us clear of the boundary without needing retry logic.
RATE_LIMIT_SLEEP = 1.1

# Same query shape that x_api_search.VACCINE_QUERY uses, for the same reasons:
# a disease term AND a vaccine term, so posts about the illness itself stay out.
VACCINE_TERMS = (
    "vaccine OR vaccines OR vaccinated OR vaccination OR vax OR vaxxed OR jab "
    "OR jabbed OR immunization OR immunisation OR booster OR shot"
)


def _build_query(disease_terms: str, brands: str = "") -> str:
    """((disease) (vaccine)) OR <brands>, minus retweets, English only.

    The pairing is what keeps "I have the flu" out of a vaccine corpus. Brand names
    sit outside it because a brand already names a vaccine on its own - nobody says
    "gardasil" about anything else.
    """
    core = "((%s) (%s))" % (disease_terms, VACCINE_TERMS)
    if brands:
        core = "(%s OR %s)" % (core, brands)
    return core + " -is:retweet lang:en"


# Ambiguous initialisms (BCG, TB, IPV, OPV) are deliberately left inside the
# disease group, never promoted to a standalone brand clause: BCG is also a
# consulting firm, IPV is also "interpersonal violence", TB is also a terabyte.
# The mandatory vaccine term is what disambiguates them.
DISEASES: dict[str, dict[str, str]] = {
    "covid19": {
        "label": "COVID-19",
        "query": _build_query(
            'covid OR covid19 OR "covid 19" OR coronavirus OR "sars-cov-2"',
            "pfizer OR biontech OR moderna OR astrazeneca OR comirnaty "
            "OR spikevax OR novavax OR janssen",
        ),
    },
    "meningitis": {
        "label": "Meningitis",
        "query": _build_query(
            "meningitis OR meningococcal OR MenACWY OR MenB",
            "bexsero OR trumenba OR menactra OR menveo OR nimenrix",
        ),
    },
    "hpv": {
        "label": "HPV",
        "query": _build_query(
            'HPV OR papillomavirus OR "papilloma virus"',
            'gardasil OR cervarix OR "cervical cancer vaccine"',
        ),
    },
    "chickenpox": {
        "label": "Chickenpox",
        # Shingles (zostavax, shingrix) is the same virus but a different vaccine,
        # so it is left out rather than quietly folded in here.
        "query": _build_query(
            'chickenpox OR "chicken pox" OR varicella',
            "varivax OR proquad",
        ),
    },
    "hepatitis_a": {
        "label": "Hepatitis A",
        # twinrix is the A+B combination, so it is omitted from both hepatitis
        # queries - including it would put the same posts in two corpora that are
        # meant to be separable.
        "query": _build_query(
            '"hepatitis a" OR "hep a" OR hepA',
            "havrix OR vaqta OR avaxim",
        ),
    },
    "hepatitis_b": {
        "label": "Hepatitis B",
        "query": _build_query(
            '"hepatitis b" OR "hep b" OR hepB',
            "engerix OR recombivax OR heplisav",
        ),
    },
    "mmr": {
        "label": "MMR",
        # proquad is MMRV, so it appears here and under chickenpox. A post can
        # legitimately land in both files; they are independent corpora.
        "query": _build_query(
            "MMR OR measles OR mumps OR rubella",
            "priorix OR proquad OR MMRV",
        ),
    },
    "tuberculosis": {
        "label": "Tuberculosis",
        "query": _build_query(
            "tuberculosis OR TB OR BCG",
            '"BCG vaccine"',
        ),
    },
    "polio": {
        "label": "Polio",
        "query": _build_query(
            "polio OR poliomyelitis OR IPV OR OPV",
            '"polio drops" OR ipol',
        ),
    },
}

QUARTERS_PER_YEAR = 4


def quarters(count: int = 8, now: datetime | None = None) -> list[tuple[str, str, str]]:
    """The last `count` calendar quarters, oldest first.

    Returns (label, start, end) with ISO 8601 bounds, e.g.
    ("2024Q2", "2024-04-01T00:00:00Z", "2024-07-01T00:00:00Z").

    Calendar quarters rather than rolling 90-day chunks, so the labels mean
    something in a report and every disease is sampled on an identical grid. The
    end of one quarter is exactly the start of the next: the API treats end_time
    as exclusive, so the windows tile without overlapping or leaving gaps.
    """
    now = now or datetime.now(timezone.utc)

    # Index the current quarter on an absolute scale, then walk backwards.
    q_index = (now.year * QUARTERS_PER_YEAR) + ((now.month - 1) // 3)

    out = []
    for i in range(count - 1, -1, -1):
        idx = q_index - i
        year, q = divmod(idx, QUARTERS_PER_YEAR)
        start = datetime(year, q * 3 + 1, 1, tzinfo=timezone.utc)
        end_year, end_q = divmod(idx + 1, QUARTERS_PER_YEAR)
        end = datetime(end_year, end_q * 3 + 1, 1, tzinfo=timezone.utc)
        # The current quarter has not finished, and the API rejects an end_time in
        # the future (it must be a little behind the request), so clamp the last
        # window to just before now.
        if end > now:
            end = now - timedelta(seconds=30)
        out.append((
            "%dQ%d" % (year, q + 1),
            start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ))
    return out


def search_all(query: str, start: str, end: str, want: int = MIN_PAGE) -> list[dict]:
    """One full-archive request for one time window.

    `want` is what we intend to keep; the request itself always asks for at least
    MIN_PAGE because the API refuses less, and we are billed for the whole page
    either way. Returns normalised dicts in x_post_fetcher's shape.
    """
    params = {
        "query": query,
        "max_results": str(min(MAX_PAGE, max(MIN_PAGE, want))),
        "start_time": start,
        "end_time": end,
        # relevancy, not recency: recency would cluster every sample at the end of
        # its quarter. Relevancy is engagement-weighted, so a small sample lands on
        # the quarter's notable posts instead of its last few hours.
        "sort_order": "relevancy",
        "tweet.fields": ("created_at,public_metrics,lang,author_id,possibly_sensitive,"
                         "referenced_tweets,in_reply_to_user_id,attachments"),
        "expansions": "author_id,in_reply_to_user_id,attachments.media_keys",
        "user.fields": "name,username,public_metrics",
        "media.fields": "url,preview_image_url,type",
    }
    data = _get(SEARCH_ALL_URL + "?" + urllib.parse.urlencode(params),
                endpoint="full-archive search")

    raw = data.get("data") or []
    includes = data.get("includes") or {}
    users = {u["id"]: u for u in includes.get("users", [])}
    media = {m["media_key"]: m for m in includes.get("media", [])}
    return [_normalise(r, users, media) for r in raw]


def fetch_disease(slug: str, per_disease: int = 24, n_quarters: int = 8,
                  keep_all: bool = False, metric: str = "likes",
                  progress=None) -> tuple[list[dict], int]:
    """Posts for one disease, spread evenly across the quarters.

    `per_disease` is split across the quarters - 24 over 8 quarters is 3 per quarter.
    Each quarter's page is ranked by `metric` and cut to that share, unless
    `keep_all` keeps everything the requests returned (which costs no more, since
    billing already happened on the full page).

    Returns (posts, billed) - `billed` being how many posts the API actually
    returned, i.e. what you paid for, as opposed to how many were kept.
    """
    if slug not in DISEASES:
        raise ValueError("unknown disease %r; expected one of %s"
                         % (slug, ", ".join(DISEASES)))

    windows = quarters(n_quarters)
    per_quarter = max(1, per_disease // len(windows))
    query = DISEASES[slug]["query"]

    kept: list[dict] = []
    billed = 0

    for n, (label, start, end) in enumerate(windows):
        if n:
            time.sleep(RATE_LIMIT_SLEEP)
        page = search_all(query, start, end, per_quarter)
        billed += len(page)

        chosen = rank_posts(page, metric) if not keep_all else page
        if not keep_all:
            chosen = chosen[:per_quarter]

        for post in chosen:
            # Extra keys are safe: XPost.from_fetch reads only the keys it knows,
            # so these dicts still load into Postgres unchanged.
            post["disease"] = slug
            post["quarter"] = label
        kept.extend(chosen)

        if progress:
            progress(label, len(page), len(chosen))

    return kept, billed


def _out_path(out_dir: str, slug: str) -> str:
    """Timestamped path that never lands on an existing file."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base = os.path.join(out_dir, "x_hist_%s_%s" % (slug, stamp))
    path, n = base + ".json", 2
    while os.path.exists(path):
        path, n = "%s-%d.json" % (base, n), n + 1
    return path


def save_disease(out_dir: str, slug: str, posts: list[dict], billed: int,
                 per_disease: int, n_quarters: int, keep_all: bool = False) -> str:
    """Write one disease's posts plus the metadata describing the sampling.

    The metadata matters more here than in a one-off search: months later, a bare
    list of posts says nothing about which query found it, which quarters it spans,
    or that only a handful per quarter were kept.
    """
    windows = quarters(n_quarters)
    run = {
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "disease": slug,
        "label": DISEASES[slug]["label"],
        "query": DISEASES[slug]["query"],
        "endpoint": "search/all",
        "sort_order": "relevancy",
        "n_quarters": n_quarters,
        "quarters": [w[0] for w in windows],
        "per_disease_target": per_disease,
        "per_quarter": "all" if keep_all else max(1, per_disease // len(windows)),
        "posts_billed": billed,
        "posts_kept": len(posts),
        "posts": posts,
    }
    path = _out_path(out_dir, slug)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(run, fh, ensure_ascii=False, indent=2)
    return path


# ---------- CLI ----------

COST_PER_POST = 0.005


def _parse_args(argv):
    p = argparse.ArgumentParser(
        prog="x_historical_search.py",
        description="Fetch vaccine posts for nine diseases, sampled by quarter.",
        epilog="Billing is per post returned and the API floor is %d per request, "
               "so a run costs about $%.2f per disease-quarter regardless of how "
               "few posts are kept." % (MIN_PAGE, MIN_PAGE * COST_PER_POST),
    )
    p.add_argument("--disease", action="append", choices=sorted(DISEASES),
                   help="repeatable; default is all nine")
    p.add_argument("--per-disease", type=int, default=24,
                   help="posts to keep per disease, split across quarters (default 24)")
    p.add_argument("--quarters", type=int, default=8,
                   help="how many quarters back to sample (default 8)")
    p.add_argument("--keep-all", action="store_true",
                   help="keep every post the requests returned - same cost, more data")
    p.add_argument("--metric", choices=["likes", "engagement"], default="likes",
                   help="what to rank each quarter's page by (default likes)")
    p.add_argument("--out-dir", default=".", help="where to write the JSON (default .)")
    p.add_argument("--dry-run", action="store_true",
                   help="print the queries, quarters and estimated cost; no API calls")
    return p.parse_args(argv)


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def _dry_run(slugs, per_disease, n_quarters) -> int:
    windows = quarters(n_quarters)
    per_quarter = max(1, per_disease // len(windows))
    requests = len(slugs) * len(windows)

    print("Quarters (%d, oldest first):" % len(windows))
    for label, start, end in windows:
        print("  %-8s %s -> %s" % (label, start[:10], end[:10]))

    print()
    print("Queries:")
    for slug in slugs:
        q = DISEASES[slug]["query"]
        ok = q.count("(") == q.count(")") and q.count('"') % 2 == 0
        print("  %-13s %4d chars  parens/quotes %s"
              % (slug, len(q), "ok" if ok else "MISMATCHED"))
        print("      %s" % q)

    print()
    minutes = max(1, round(requests * RATE_LIMIT_SLEEP / 60))
    print("Plan: %d %s x %d quarters = %d requests, keeping %d per quarter."
          % (len(slugs), _plural(len(slugs), "disease", "diseases"),
             len(windows), requests, per_quarter))
    print("Billed ~%d posts (the API floor of %d per request), about $%.2f."
          % (requests * MIN_PAGE, MIN_PAGE, requests * MIN_PAGE * COST_PER_POST))
    print("Throttled to 1 request/second, so expect roughly %d %s."
          % (minutes, _plural(minutes, "minute", "minutes")))
    return 0


def main(argv=None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    slugs = args.disease or sorted(DISEASES)

    if args.dry_run:
        return _dry_run(slugs, args.per_disease, args.quarters)

    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    except ImportError:
        pass

    if args.out_dir != "." and not os.path.isdir(args.out_dir):
        os.makedirs(args.out_dir, exist_ok=True)

    total_billed = 0
    for slug in slugs:
        print("%s (%s)" % (DISEASES[slug]["label"], slug), file=sys.stderr)

        def progress(label, got, kept, _slug=slug):
            print("  %-8s %2d returned, %2d kept" % (label, got, kept),
                  file=sys.stderr)

        try:
            posts, billed = fetch_disease(
                slug, per_disease=args.per_disease, n_quarters=args.quarters,
                keep_all=args.keep_all, metric=args.metric, progress=progress)
        except XAPIError as e:
            print("error: %s" % e, file=sys.stderr)
            if total_billed:
                print("stopped after ~%d posts billed (about $%.2f)."
                      % (total_billed, total_billed * COST_PER_POST), file=sys.stderr)
            return 1

        total_billed += billed
        path = save_disease(args.out_dir, slug, posts, billed,
                            args.per_disease, args.quarters, args.keep_all)
        print("  -> %d posts kept of %d billed, saved to %s"
              % (len(posts), billed, path), file=sys.stderr)

    print("\nDone. ~%d posts billed across %d %s, about $%.2f."
          % (total_billed, len(slugs), _plural(len(slugs), "disease", "diseases"),
             total_billed * COST_PER_POST), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
