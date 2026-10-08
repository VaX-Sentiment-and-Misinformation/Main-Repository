#!/usr/bin/env python3
"""
fetch_week.py - the most-interacted vaccine posts of the last 7 days.

Feeds the "Trending posts" cards on the home and Trends pages (see
backend/scripts/build_trending_posts.py). Same Actor, query groups, engagement
floor and window checks as fetch_monthly - this only swaps the calendar month for
a rolling 7-day window ending today, so read fetch_monthly's HISTORY before
changing anything about how the window is asked for.

    python -m apify.fetch_week --dry-run      # free, shows the plan
    python -m apify.fetch_week                # ~1,000 posts, ~$0.40

Output: apify_vax_week-<end>.json in the same format as the monthly files.
Keep it out of the folder of monthly files: predict_historical_sentiment.py
reads every apify_vax_*.json there, and the week would double-count.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

from .client import ApifyError
from .diseases import query_groups
from .fetch_monthly import (COST_PER_POST, DEFAULT_MAX_ITEMS,
                            DEFAULT_MIN_FAVORITES, SORT, _floor_warning,
                            _window_failure, effective_total, fetch_month,
                            out_path, save_month)

DAYS = 7


def window(now=None) -> tuple[str, str, str]:
    """(label, start, end) for the last DAYS full days, `end` exclusive.

    Ends at today rather than now: X's `until:` takes a date, and asking for a
    window that runs into the future would be clamped anyway.
    """
    end = (now or datetime.now(timezone.utc)).date()
    start = end - timedelta(days=DAYS)
    return "week-%s" % end.isoformat(), start.isoformat(), end.isoformat()


def _parse_args(argv):
    p = argparse.ArgumentParser(
        prog="fetch_week.py",
        description="Top vaccine posts of the last %d days via the Apify "
                    "tweet-scraper Actor." % DAYS,
    )
    p.add_argument("--max-items", type=int, default=DEFAULT_MAX_ITEMS,
                   help="posts for the week (default %d)" % DEFAULT_MAX_ITEMS)
    p.add_argument("--min-favorites", type=int, default=DEFAULT_MIN_FAVORITES,
                   help="engagement floor (default %d)" % DEFAULT_MIN_FAVORITES)
    p.add_argument("--out-dir", default=".", help="where to write the JSON (default .)")
    p.add_argument("--force", action="store_true",
                   help="re-fetch if today's file already exists")
    p.add_argument("--dry-run", action="store_true",
                   help="print the window and cost; no API calls, no spend")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    label, start, end = window()
    n_groups = len(query_groups())
    billed = effective_total(args.max_items, n_groups)

    print("%s  %s -> %s, %d groups, ~%d posts billed, about $%.2f. Sort: %s, "
          "minimumFavorites=%d."
          % (label, start, end, n_groups, billed, billed * COST_PER_POST, SORT,
             args.min_favorites), file=sys.stderr)
    warning = _floor_warning(args.max_items, n_groups)
    if warning:
        print("warning: %s" % warning, file=sys.stderr)
    if args.dry_run:
        return 0

    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    except ImportError:
        pass

    path = out_path(args.out_dir, label)
    # Paid data: a second run on the same day must not buy the week again.
    if os.path.exists(path) and not args.force:
        print("%s already fetched, skipping (--force to redo)" % path, file=sys.stderr)
        return 0
    os.makedirs(args.out_dir, exist_ok=True)

    def on_poll(status, waited):
        print("      ... %s (%ds)" % (status.lower(), waited), file=sys.stderr)

    def on_group(slugs, share):
        print("  [%s] up to %d posts" % (", ".join(slugs), share), file=sys.stderr)

    try:
        posts, stats = fetch_month(label, start, end, args.max_items,
                                   on_poll=on_poll, on_group=on_group,
                                   min_favorites=args.min_favorites)
    except ApifyError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1

    broken = _window_failure(label, stats)
    if broken:
        print("     %s" % broken, file=sys.stderr)
        print("     Not saving. %d posts billed (about $%.2f)."
              % (stats["billed"], stats["billed"] * COST_PER_POST), file=sys.stderr)
        return 1

    saved = save_month(args.out_dir, label, start, end, posts, args.max_items,
                       stats, args.min_favorites)
    print("  -> %d kept of %d billed, about $%.2f, saved to %s"
          % (len(posts), stats["billed"], stats["billed"] * COST_PER_POST, saved),
          file=sys.stderr)
    print("     window: %d in, %d out, %d undated; spans %.0f%% of the week over "
          "%d days"
          % (stats["in_window"], stats["out_of_window"], stats["undated"],
             100 * stats["coverage"], stats["days_present"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
