#!/usr/bin/env python3
"""
fetch_monthly.py - the top N most-interacted vaccine posts of each month.

Plan B for x_historical_search.py. That module uses the official X full-archive
endpoint, which needs a Self-serve or Enterprise entitlement the project does not
have, and costs $5.00 per 1,000 posts. This goes through the Apify
apidojo/tweet-scraper Actor instead: no entitlement beyond a token, $0.40 per
1,000 posts, and - unlike the official API - it can actually sort by engagement.

    python -m apify.fetch_monthly --dry-run      # free, shows the plan
    python -m apify.fetch_monthly                # 36 months, ~$14.40

The sampling is deliberately NOT per-disease. One combined query covers all nine
diseases, so the top 1,000 of a month is the top 1,000 across vaccine discourse as
a whole rather than 1,000 per disease. Each post is then tagged with the disease
or diseases it mentions, so the corpus can still be sliced afterwards.

Output: one JSON per month, apify_vax_<YYYY-MM>.json, holding run metadata and the
posts in the project's standard dict shape - so XPost.from_fetch loads them
unchanged whenever the Postgres side is wired up.
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone

from .client import ApifyError, run_actor
from .diseases import (APPENDED_CHARS, DISEASES, X_QUERY_LIMIT, combined_query,
                       query_groups, tag, tag_counts)
from .normalise import engagement, normalise

__all__ = ["months", "fetch_month", "save_month"]

# $0.40 per 1,000 tweets, per the Actor's published pricing.
COST_PER_POST = 0.0004
# The Actor documents a 50-tweet minimum per query; asking for less is rejected.
MIN_ITEMS = 50
DEFAULT_MONTHS = 36
DEFAULT_MAX_ITEMS = 1000


def months(count: int = DEFAULT_MONTHS, now: date | None = None
           ) -> list[tuple[str, str, str]]:
    """The last `count` calendar months, oldest first.

    Returns (label, start, end) as ("2024-03", "2024-03-01", "2024-04-01"), with
    `end` exclusive so consecutive months tile without overlapping. The current
    month has not finished, so its end is clamped to today - asking the Actor for
    a future window would either error or silently return nothing.
    """
    now = now or datetime.now(timezone.utc).date()
    index = now.year * 12 + (now.month - 1)

    out = []
    for i in range(count - 1, -1, -1):
        idx = index - i
        year, month = divmod(idx, 12)
        start = date(year, month + 1, 1)
        end_year, end_month = divmod(idx + 1, 12)
        end = date(end_year, end_month + 1, 1)
        if end > now:
            end = now
        out.append(("%04d-%02d" % (year, month + 1),
                    start.isoformat(), end.isoformat()))
    return out


def actor_input(query: str, start: str, end: str, max_items: int) -> dict:
    """The Actor input for one disease group in one month.

    Only fields from the published input schema - no invented parameters. Language
    goes through `tweetLanguage` rather than a lang: operator in the query: the
    schema provides the field, and every character in the query counts against
    X's 512-char search limit.

    One query per call, deliberately. `searchTerms` accepts an array, but the
    Actor walks it sequentially against one run-wide maxItems, so a high-volume
    group (COVID) would consume the whole budget before the others ran.
    """
    return {
        "searchTerms": [query],
        "start": start,
        "end": end,
        # "Top" is X's engagement-weighted tab. It is the whole reason this path
        # beats the official API, which cannot sort by engagement at all.
        "sort": "Top",
        "maxItems": max(MIN_ITEMS, max_items),
        "tweetLanguage": "en",
    }


def share_per_group(max_items: int, n_groups: int) -> int:
    """How many posts to request from each group.

    The Actor refuses a request below MIN_ITEMS, so a small --max-items spread
    over several groups gets floored upward and the run fetches MORE than asked
    for: 100 over 4 groups wants 25 each, but 50 is the minimum, so 200 come back.
    Billing is per post returned, so that overshoot is real money - which is why
    effective_total() exists and the CLI warns about it rather than letting it be
    discovered in the logs.
    """
    return max(MIN_ITEMS, max_items // n_groups)


def effective_total(max_items: int, n_groups: int) -> int:
    """Posts actually fetched and billed per month, floor included."""
    return share_per_group(max_items, n_groups) * n_groups


def fetch_month(label: str, start: str, end: str,
                max_items: int = DEFAULT_MAX_ITEMS, on_poll=None,
                on_group=None) -> tuple[list[dict], int]:
    """One month's posts: fetched per disease group, normalised, tagged, ranked.

    Returns (kept, stats). `stats` accounts for every post that was paid for, so
    the difference between what was billed and what is on disk is never a mystery:

        billed      posts the Actor returned - what you are charged for
        duplicates  returned by a second group's query, stored once
        no_id       returned without an id, unusable
        collected   unique, usable posts
        kept        collected, cut to max_items

    Duplicates are expected, not a fault: a post about both MMR and chickenpox
    can be in the top results of two different group queries, and X charges for
    each copy.

    The nine diseases do not fit in one query (see diseases.query_groups), so this
    is one Actor run per group with the month's allocation split evenly between
    them. Even shares rather than a single global top-N: COVID volume dwarfs the
    other eight, so one pooled ranking would come back almost entirely COVID and
    be useless for comparing diseases.

    Asks the Actor for "Top", then re-sorts locally by total engagement. X's "Top"
    is undocumented, so the saved order is a stated arithmetic rule
    (likes + reposts + replies + quotes) rather than something opaque.

    De-duplicates on post id: the groups overlap a little (proquad is both MMR and
    chickenpox), and a post matching two groups would otherwise appear twice.
    """
    groups = query_groups()
    share = share_per_group(max_items, len(groups))

    posts: list[dict] = []
    seen: set[str] = set()
    stats = {"billed": 0, "duplicates": 0, "no_id": 0}

    for slugs, query in groups:
        if on_group:
            on_group(slugs, share)
        items = run_actor(actor_input(query, start, end, share), on_poll=on_poll)
        stats["billed"] += len(items)
        for item in items:
            post = normalise(item)
            if not post["id"]:
                stats["no_id"] += 1
                continue
            if post["id"] in seen:
                stats["duplicates"] += 1
                continue
            seen.add(post["id"])
            post["month"] = label
            post["diseases"] = tag(post["text"])
            posts.append(post)

    posts.sort(key=engagement, reverse=True)
    stats["collected"] = len(posts)
    kept = posts[:max_items]
    stats["kept"] = len(kept)
    return kept, stats


def out_path(out_dir: str, label: str) -> str:
    return os.path.join(out_dir, "apify_vax_%s.json" % label)


def save_month(out_dir: str, label: str, start: str, end: str,
               posts: list[dict], max_items: int, stats: dict) -> str:
    """Write one month, with the metadata needed to interpret it later.

    The `stats` from fetch_month go in verbatim, so anyone opening the file can
    reconcile what was paid for against what is in it without re-deriving it.
    """
    run = {
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "apify/apidojo~tweet-scraper",
        "month": label,
        "start": start,
        "end": end,
        # The query actually sent, one per disease group - the nine do not fit
        # in a single 512-char X search.
        "queries": [{"diseases": slugs, "query": q} for slugs, q in query_groups()],
        "sort_requested": "Top",
        "ranked_by": "likes + reposts + replies + quotes",
        "max_items": max_items,
        "requested_per_group": share_per_group(max_items, len(query_groups())),
        # Accounts for every post paid for: billed = kept + duplicates + no_id
        # + anything cut past max_items. A post matching two group queries is
        # returned - and charged - twice, but stored once.
        "posts_billed": stats["billed"],
        "posts_duplicate": stats["duplicates"],
        "posts_without_id": stats["no_id"],
        "posts_collected": stats["collected"],
        "posts_kept": len(posts),
        "estimated_cost_usd": round(stats["billed"] * COST_PER_POST, 4),
        # Overlapping counts: these sum to more than posts_kept, because a
        # post mentioning two diseases is counted under both.
        "disease_counts": tag_counts(posts),
        "untagged": sum(1 for p in posts if not p["diseases"]),
        "posts": posts,
    }
    path = out_path(out_dir, label)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(run, fh, ensure_ascii=False, indent=2)
    return path


# ---------- CLI ----------

def _parse_args(argv):
    p = argparse.ArgumentParser(
        prog="fetch_monthly.py",
        description="Top vaccine posts per month via the Apify tweet-scraper Actor.",
        epilog="Apify bills $0.40 per 1,000 tweets, so a full 36-month run at "
               "1,000 a month is about $14.40.",
    )
    p.add_argument("--months", type=int, default=DEFAULT_MONTHS,
                   help="how many months back to cover (default %d)" % DEFAULT_MONTHS)
    p.add_argument("--month", action="append", metavar="YYYY-MM",
                   help="repeatable; fetch only these months")
    p.add_argument("--max-items", type=int, default=DEFAULT_MAX_ITEMS,
                   help="posts per month (default %d, Actor minimum %d)"
                        % (DEFAULT_MAX_ITEMS, MIN_ITEMS))
    p.add_argument("--out-dir", default=".", help="where to write the JSON (default .)")
    p.add_argument("--force", action="store_true",
                   help="re-fetch months whose file already exists")
    p.add_argument("--dry-run", action="store_true",
                   help="print the query, months and cost; no API calls, no spend")
    p.add_argument("--preflight", action="store_true",
                   help="run every offline check and print a verdict; no spend")
    return p.parse_args(argv)


def _floor_warning(max_items: int, n_groups: int) -> str | None:
    """Warn when the Actor's per-request minimum makes us overshoot max_items.

    Silent overshoot is money: --max-items 100 across 4 groups requests 50 each
    because 25 is below the floor, so 200 posts are fetched and charged for while
    only 100 are kept.
    """
    per_month = effective_total(max_items, n_groups)
    if per_month <= max_items:
        return None
    return ("--max-items %d over %d groups is %d each, below the Actor's %d "
            "minimum, so each group is asked for %d: %d posts fetched and billed "
            "per month, %d kept. Use --max-items %d or more to stop overshooting."
            % (max_items, n_groups, max_items // n_groups, MIN_ITEMS,
               share_per_group(max_items, n_groups), per_month, max_items,
               MIN_ITEMS * n_groups))


def _dry_run(windows, max_items) -> int:
    groups = query_groups()
    share = share_per_group(max_items, len(groups))
    billed = len(windows) * effective_total(max_items, len(groups))

    print("All nine in one query would be %d chars - over X's 512-char limit, "
          "which returns zero" % len(combined_query()))
    print("results rather than an error. Split into %d groups:" % len(groups))
    print()
    for n, (slugs, q) in enumerate(groups, 1):
        balanced = q.count("(") == q.count(")") and q.count('"') % 2 == 0
        print("  group %d  %3d chars (+42 appended by Apify = %3d)  %s  [%s]"
              % (n, len(q), len(q) + 42, "ok" if balanced else "MISMATCHED",
                 ", ".join(slugs)))
        print("    %s" % q)
    print()
    print("Covers %d diseases: %s"
          % (len(DISEASES), ", ".join(d["label"] for d in DISEASES.values())))
    print()
    print("Months (%d, oldest first):" % len(windows))
    for label, start, end in windows:
        print("  %-9s %s -> %s" % (label, start, end))
    print()
    print("Plan: %d months x %d groups = %d runs, %d posts each = ~%d posts "
          "billed, about $%.2f."
          % (len(windows), len(groups), len(windows) * len(groups), share,
             billed, billed * COST_PER_POST))
    warning = _floor_warning(max_items, len(groups))
    if warning:
        print()
        print("WARNING: %s" % warning)
    return 0


def _preflight() -> int:
    """Everything checkable without paying, plus an honest note on what is not.

    Exists so "is it safe to spend money on this?" is one command with a verdict,
    rather than trust in someone's summary.
    """
    import unittest

    print("=" * 68)
    print("PREFLIGHT - no API calls, nothing billed")
    print("=" * 68)

    suite = unittest.defaultTestLoader.loadTestsFromName("apify.selftest")
    result = unittest.TextTestRunner(verbosity=1, stream=sys.stderr).run(suite)

    groups = query_groups()
    print()
    print("Queries: %d groups, longest %d chars (%d sent). X answers anything "
          "over %d"
          % (len(groups), max(len(q) for _, q in groups),
             max(len(q) for _, q in groups) + APPENDED_CHARS, X_QUERY_LIMIT))
    print("  with zero results, so every group is kept under a length measured "
          "to work.")
    print()

    if not result.wasSuccessful():
        print("VERDICT: NOT READY - %d failure(s). Do not upgrade yet."
              % (len(result.failures) + len(result.errors)))
        return 1

    print("VERDICT: every offline check passes.")
    print()
    print("  Proven: query lengths, disease coverage, tagging, monthly windows,")
    print("          ranking, de-duplication, file writing, and that a saved post")
    print("          loads back into XPost. Also proven live earlier: auth, run")
    print("          creation, polling, date translation, sort and language.")
    print()
    print("  NOT proven: that these specific queries return posts from X. That")
    print("          needs one paid run. Do the cheap one first:")
    print("              python -m apify.fetch_monthly --month 2026-08 "
          "--max-items 200")
    print("          ~%d posts, about $%.2f. Check disease_counts covers more"
          % (200, 200 * COST_PER_POST))
    print("          than COVID before committing to the full 36 months.")
    return 0


def main(argv=None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    if args.preflight:
        return _preflight()

    windows = months(args.months)
    if args.month:
        wanted = set(args.month)
        windows = [w for w in windows if w[0] in wanted]
        missing = wanted - {w[0] for w in windows}
        if missing:
            print("error: %s not in the last %d months"
                  % (", ".join(sorted(missing)), args.months), file=sys.stderr)
            return 2

    if args.dry_run:
        return _dry_run(windows, args.max_items)

    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    except ImportError:
        pass

    if args.out_dir != "." and not os.path.isdir(args.out_dir):
        os.makedirs(args.out_dir, exist_ok=True)

    # Say this before spending, not after: the floor can make the run fetch more
    # than --max-items asked for, and every extra post is charged.
    warning = _floor_warning(args.max_items, len(query_groups()))
    if warning:
        print("warning: %s" % warning, file=sys.stderr)
        print(file=sys.stderr)

    total_kept = 0
    total_billed = 0
    for label, start, end in windows:
        path = out_path(args.out_dir, label)
        # This is paid data. A rerun after a failure partway through must not
        # buy the earlier months a second time.
        if os.path.exists(path) and not args.force:
            print("%s  already fetched, skipping (--force to redo)" % label,
                  file=sys.stderr)
            continue

        print("%s  %s -> %s" % (label, start, end), file=sys.stderr)

        def on_poll(status, waited, _label=label):
            print("      ... %s (%ds)" % (status.lower(), waited), file=sys.stderr)

        def on_group(slugs, share, _label=label):
            print("  [%s] up to %d posts" % (", ".join(slugs), share),
                  file=sys.stderr)

        try:
            posts, stats = fetch_month(label, start, end, args.max_items,
                                       on_poll=on_poll, on_group=on_group)
        except ApifyError as e:
            print("error: %s" % e, file=sys.stderr)
            if total_billed:
                print("stopped after %d posts billed (about $%.2f)."
                      % (total_billed, total_billed * COST_PER_POST),
                      file=sys.stderr)
            return 1

        total_kept += len(posts)
        total_billed += stats["billed"]
        saved = save_month(args.out_dir, label, start, end, posts,
                           args.max_items, stats)
        tagged = sum(1 for p in posts if p["diseases"])
        # Name the duplicates rather than leaving a silent gap between the two
        # numbers - that gap is the first thing anyone asks about.
        gap = ""
        if stats["duplicates"] or stats["no_id"]:
            parts = []
            if stats["duplicates"]:
                parts.append("%d dup" % stats["duplicates"])
            if stats["no_id"]:
                parts.append("%d no id" % stats["no_id"])
            gap = ", %s" % ", ".join(parts)
        print("  -> %d kept of %d billed (%d tagged%s), saved to %s"
              % (len(posts), stats["billed"], tagged, gap, saved), file=sys.stderr)

    print(file=sys.stderr)
    print("Done. %d posts kept, %d billed, about $%.2f."
          % (total_kept, total_billed, total_billed * COST_PER_POST),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
