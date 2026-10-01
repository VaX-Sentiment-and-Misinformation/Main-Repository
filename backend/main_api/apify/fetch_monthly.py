#!/usr/bin/env python3
"""
fetch_monthly.py - the top N most-interacted vaccine posts of each month.

Plan B for x_historical_search.py. That module uses the official X full-archive
endpoint, which needs a Self-serve or Enterprise entitlement the project does not
have, and costs $5.00 per 1,000 posts. This goes through the Apify
apidojo/tweet-scraper Actor instead: no entitlement beyond a token and $0.40 per
1,000 posts.

    python -m apify.fetch_monthly --dry-run      # free, shows the plan
    python -m apify.fetch_monthly --verify       # free, audits files on disk
    python -m apify.fetch_monthly                # 36 months, ~$14.40

HISTORY - read this before touching `sort`. The first full run of this module was
worthless and cost $14.28. It used sort="Top", because "Top" is X's
engagement-weighted tab and ranking by engagement was the whole reason for
choosing Apify. But X's Top tab does not apply `until:`. The Actor translated the
month window into the query correctly - its log proves it:

    Got 20 results for (...) lang:en since:2023-10-01 until:2023-11-01. Sort: Top

and X returned current posts anyway: 214 of the 250 posts in that October-2023 run
were created in September 2026, the week the run happened. Across 36 months, 97%
of posts fell outside their own file's month, and the 33,325 rows on disk held
only 2,496 unique posts - one month of data, bought 36 times. The Actor's README
says as much: "If you are getting low results ... try using `sort: Top`" and, of
the start/end fields, "the best way is to use Twitter queries".

So engagement ranking and a working date window cannot both come from `sort`. This
module now takes the window from sort="Latest" and the engagement selection from
minimumFavorites, then ranks locally as it always did. Nothing here trusts that
silently: every post is checked against the window it was filed under, and the
coverage warning fires when a month's posts bunch at one end of it.

The sampling is deliberately NOT per-disease. One combined query covers all nine
diseases, so the top 1,000 of a month is the top 1,000 across vaccine discourse as
a whole rather than 1,000 per disease. Each post is then tagged with the disease
or diseases it mentions, so the corpus can still be sliced afterwards.

Output: one JSON per month, apify_vax_<YYYY-MM>.json, holding run metadata and the
posts in the project's standard dict shape - so XPost.from_fetch loads them
unchanged whenever the Postgres side is wired up.
"""

import argparse
import glob
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

# Must stay "Latest". "Top" ignores `until:` - see HISTORY above. "Latest + Top"
# runs both and so reintroduces the same unwindowed results.
SORT = "Latest"

# With sort="Latest" X walks backwards from `until:`, so a month's allocation is
# its MOST RECENT posts, not its best. Left unbounded that means 250 posts from
# the last few days of the month. The engagement floor is what thins the pool
# enough for an allocation to span the whole month, which makes it a correctness
# setting and not just a quality one.
#
# 100 is a starting point, not a measured value: the right floor is the one where
# a month returns somewhat more than max_items. Too low wastes the budget on the
# end of the month, too high returns under the Actor's 50-item minimum. Calibrate
# on one month before committing to 36 - the coverage line printed per month, and
# --verify afterwards, both show whether it is working.
DEFAULT_MIN_FAVORITES = 100

# Below this share of the month spanned by the kept posts, say so. Recency bias
# from sort="Latest" is the expected cause, and the fix is a higher floor.
MIN_WINDOW_COVERAGE = 0.5


def months(count: int = DEFAULT_MONTHS, now: date | None = None
           ) -> list[tuple[str, str, str]]:
    """The last `count` calendar months, oldest first.

    Returns (label, start, end) as ("2024-03", "2024-03-01", "2024-04-01"), with
    `end` exclusive so consecutive months tile without overlapping. The current
    month has not finished, so its end is clamped to today - asking the Actor for
    a future window would either error or silently return nothing.

    That clamp can empty a window entirely: run this on the 1st and the current
    month is 2026-10-01 -> 2026-10-01, nothing at all. Such a month is dropped
    rather than sent, because the Actor returns no posts for it and client.py
    treats an empty run as an error - which would fail the whole command on its
    last step, after every other month had been paid for. So the list can be
    shorter than `count`; a month with no elapsed days is not fetchable.
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
        if start >= end:
            continue
        out.append(("%04d-%02d" % (year, month + 1),
                    start.isoformat(), end.isoformat()))
    return out


def actor_input(query: str, start: str, end: str, max_items: int,
                min_favorites: int = DEFAULT_MIN_FAVORITES) -> dict:
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
        # Not "Top", however much this module wants engagement ordering: X's Top
        # tab ignores `until:` and returns currently-popular posts for every
        # window asked for. See HISTORY at the top of this file.
        "sort": SORT,
        # The engagement selection "Top" was supposed to provide, as a filter
        # instead of a sort - and the reason an allocation can span the month.
        "minimumFavorites": min_favorites,
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


def created_on(post: dict) -> date | None:
    """The UTC date a post was created, or None if its timestamp will not parse.

    Reuses models.parse_x_time rather than re-deriving the format, so the window
    check and the database agree about what a post's date is. Imported inside the
    function: models pulls in SQLModel, and this is a CLI that must keep working
    when only the Actor side is being exercised.
    """
    from models import parse_x_time

    when = parse_x_time(post.get("created_at"))
    return when.astimezone(timezone.utc).date() if when else None


def split_by_window(posts: list[dict], start: str, end: str
                    ) -> tuple[list[dict], list[dict], list[dict]]:
    """Partition posts into (inside the window, outside it, undated).

    `end` is exclusive, matching months(). This is the check that the first run of
    this module did not have: it asked X for a month, X answered with whatever was
    popular that week, and nothing compared the two until the corpus was paid for.
    A post that cannot be placed in the window is not kept - a file named
    apify_vax_2024-06.json should contain June 2024 or say why it does not.
    """
    first = date.fromisoformat(start)
    last = date.fromisoformat(end)

    inside, outside, undated = [], [], []
    for post in posts:
        when = created_on(post)
        if when is None:
            undated.append(post)
        elif first <= when < last:
            inside.append(post)
        else:
            outside.append(post)
    return inside, outside, undated


def coverage(posts: list[dict], start: str, end: str) -> tuple[float, int]:
    """What share of the window the posts actually span, and over how many days.

    sort="Latest" hands back the newest posts in the window first, so an
    allocation that is small relative to the pool covers only the window's tail.
    That is a real sampling bias and it is invisible in a post count, so it gets
    measured: span of kept dates divided by the length of the window.
    """
    window_days = max((date.fromisoformat(end) - date.fromisoformat(start)).days, 1)
    days = sorted({d for d in (created_on(p) for p in posts) if d})
    if not days:
        return 0.0, 0
    spanned = (days[-1] - days[0]).days + 1
    return min(spanned / window_days, 1.0), len(days)


def fetch_month(label: str, start: str, end: str,
                max_items: int = DEFAULT_MAX_ITEMS, on_poll=None,
                on_group=None,
                min_favorites: int = DEFAULT_MIN_FAVORITES
                ) -> tuple[list[dict], dict]:
    """One month's posts: fetched per disease group, normalised, tagged, ranked.

    Returns (kept, stats). `stats` accounts for every post that was paid for, so
    the difference between what was billed and what is on disk is never a mystery:

        billed        posts the Actor returned - what you are charged for
        duplicates    returned by a second group's query, stored once
        no_id         returned without an id, unusable
        collected     unique, usable posts
        out_of_window created outside [start, end) - dropped, see below
        undated       timestamp would not parse - dropped, cannot be placed
        in_window     collected, minus the two above
        kept          in_window, cut to max_items

    Duplicates are expected, not a fault: a post about both MMR and chickenpox
    can be in the top results of two different group queries, and X charges for
    each copy.

    The nine diseases do not fit in one query (see diseases.query_groups), so this
    is one Actor run per group with the month's allocation split evenly between
    them. Even shares rather than a single global top-N: COVID volume dwarfs the
    other eight, so one pooled ranking would come back almost entirely COVID and
    be useless for comparing diseases.

    Asks the Actor for "Latest" above an engagement floor, then re-sorts locally by
    total engagement, so the saved order is a stated arithmetic rule
    (likes + reposts + replies + quotes) rather than something opaque.

    `out_of_window` should be 0 or near it. It is not merely reported but enforced:
    posts outside the month are dropped rather than filed under it. A non-trivial
    count means X is not honouring the window, which is exactly the failure that
    made the first full run of this module worthless - so it is surfaced per month
    by the CLI rather than left in the file for someone to notice later.

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
        items = run_actor(actor_input(query, start, end, share, min_favorites),
                          on_poll=on_poll)
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

    stats["collected"] = len(posts)
    inside, outside, undated = split_by_window(posts, start, end)
    stats["out_of_window"] = len(outside)
    stats["undated"] = len(undated)
    stats["in_window"] = len(inside)

    inside.sort(key=engagement, reverse=True)
    kept = inside[:max_items]
    stats["kept"] = len(kept)
    stats["coverage"], stats["days_present"] = coverage(kept, start, end)
    return kept, stats


def out_path(out_dir: str, label: str) -> str:
    return os.path.join(out_dir, "apify_vax_%s.json" % label)


def save_month(out_dir: str, label: str, start: str, end: str,
               posts: list[dict], max_items: int, stats: dict,
               min_favorites: int = DEFAULT_MIN_FAVORITES) -> str:
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
        "sort_requested": SORT,
        # Recorded because it decides which posts could appear at all, so a file
        # cannot be compared with another month's without knowing it.
        "min_favorites": min_favorites,
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
        # The window audit. posts_out_of_window must stay at or near 0; anything
        # else means X did not honour since:/until: and the file is not the month
        # it claims to be.
        "posts_out_of_window": stats["out_of_window"],
        "posts_undated": stats["undated"],
        "posts_in_window": stats["in_window"],
        "posts_kept": len(posts),
        # Share of the month spanned by the kept posts. Well under 1.0 means the
        # allocation ran out before the start of the month - raise min_favorites.
        "window_coverage": round(stats["coverage"], 3),
        "days_present": stats["days_present"],
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
    p.add_argument("--min-favorites", type=int, default=DEFAULT_MIN_FAVORITES,
                   help="engagement floor; also what makes a month's posts span "
                        "the month rather than its last days (default %d)"
                        % DEFAULT_MIN_FAVORITES)
    p.add_argument("--out-dir", default=".", help="where to write the JSON (default .)")
    p.add_argument("--force", action="store_true",
                   help="re-fetch months whose file already exists")
    p.add_argument("--dry-run", action="store_true",
                   help="print the query, months and cost; no API calls, no spend")
    p.add_argument("--preflight", action="store_true",
                   help="run every offline check and print a verdict; no spend")
    p.add_argument("--verify", action="store_true",
                   help="audit the month files already on disk against the "
                        "windows they claim; no API calls, no spend")
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


def _window_failure(label: str, stats: dict) -> str | None:
    """Why this month must not be written, or None if it is fit to save.

    Two shapes of the same fault - X not applying since:/until:. Nothing in the
    month at all is unambiguous. More posts outside the window than inside says
    the window is being treated as a suggestion, which is what sort="Top" did on
    every one of 144 runs.
    """
    stray = stats["out_of_window"] + stats["undated"]
    if stats["in_window"] == 0:
        return ("FAILED: not one of %d posts is from %s. X is not applying the "
                "date window - check `sort` is %r and read the Actor run log."
                % (stats["collected"], label, SORT))
    if stray > stats["in_window"]:
        return ("FAILED: %d of %d posts are from outside %s, more than are "
                "inside it. The date window is not being honoured."
                % (stray, stats["collected"], label))
    return None


def _dry_run(windows, max_items, min_favorites=DEFAULT_MIN_FAVORITES) -> int:
    groups = query_groups()
    share = share_per_group(max_items, len(groups))
    billed = len(windows) * effective_total(max_items, len(groups))

    print("All nine in one query would be %d chars - over X's 512-char limit, "
          "which returns zero" % len(combined_query()))
    print("results rather than an error. Split into %d groups:" % len(groups))
    print()
    for n, (slugs, q) in enumerate(groups, 1):
        balanced = q.count("(") == q.count(")") and q.count('"') % 2 == 0
        print("  group %d  %3d chars (+%d appended by Apify = %3d)  %s  [%s]"
              % (n, len(q), APPENDED_CHARS, len(q) + APPENDED_CHARS,
                 "ok" if balanced else "MISMATCHED", ", ".join(slugs)))
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
    print("Sort: %s with minimumFavorites=%d. NOT \"Top\" - Top ignores until: "
          "and returns" % (SORT, min_favorites))
    print("      current posts for every window asked for; that is what made the")
    print("      first full run of this module worthless.")
    print("Every post is checked against its month, and months whose posts bunch")
    print("at the end of the window are reported. Audit later with --verify.")
    warning = _floor_warning(max_items, len(groups))
    if warning:
        print()
        print("WARNING: %s" % warning)
    return 0


def _verify(out_dir: str, _windows=None) -> int:
    """Audit the month files on disk: do their posts fall in the month they name?

    Offline and free. Exists because the skip-if-exists rule in main() protects
    paid data, which is only a kindness when the data is right - after the
    sort="Top" run it meant 36 wrong files would be preserved by every rerun. This
    names the ones to delete or --force.

    Walks the directory rather than the rolling window from months(), and judges
    each file against the start/end recorded inside it. A file that has aged out
    of the last 36 months still needs auditing, and a file should be held to the
    window it actually claims rather than one recomputed from today's date.
    """
    paths = sorted(glob.glob(os.path.join(out_dir, "apify_vax_*.json")))
    if not paths:
        print("No apify_vax_*.json in %s - nothing to audit." % out_dir)
        return 0

    print("Auditing %d file(s) in %s against the months they claim. No API calls."
          % (len(paths), out_dir))
    print()
    print("%-9s %7s %7s %7s %6s  %s"
          % ("month", "posts", "in", "out", "cover", "verdict"))

    bad, ok = [], []
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            run = json.load(fh)
        label = run.get("month") or os.path.basename(path)[10:-5]
        start, end = run.get("start"), run.get("end")
        if not start or not end:
            # Pre-dates the metadata, or hand-edited: derive the window from the
            # label rather than skipping the file and calling it clean.
            first = date.fromisoformat(label + "-01")
            start = first.isoformat()
            end = date(first.year + first.month // 12,
                       first.month % 12 + 1, 1).isoformat()

        posts = run.get("posts") or []
        inside, outside, undated = split_by_window(posts, start, end)
        stray = len(outside) + len(undated)
        share, _days = coverage(inside, start, end)

        if stray:
            # Any post outside the window means the window was not applied, so
            # coverage of the survivors says nothing useful - don't print a
            # reassuring number next to a failure.
            cover, verdict = "-", "REFETCH - %d of %d not from %s" % (
                stray, len(posts), label)
            bad.append(label)
        elif not posts:
            cover, verdict = "-", "REFETCH - empty"
            bad.append(label)
        elif share < MIN_WINDOW_COVERAGE:
            cover = "%.0f%%" % (100 * share)
            verdict = "thin - raise --min-favorites and refetch"
            bad.append(label)
        else:
            cover, verdict = "%.0f%%" % (100 * share), "ok"
            ok.append(label)
        print("%-9s %7d %7d %7d %6s  %s"
              % (label, len(posts), len(inside), stray, cover, verdict))

    print()
    if not bad:
        print("VERDICT: all %d file(s) hold the month they name." % len(ok))
        return 0

    print("VERDICT: %d of %d file(s) do not hold the month they name."
          % (len(bad), len(bad) + len(ok)))
    print()
    print("A file whose posts are from the wrong month has nothing of that month")
    print("in it, so filtering cannot save it - it has to be fetched again.")
    print()
    if not ok:
        print("    python -m apify.fetch_monthly --force")
    else:
        print("    python -m apify.fetch_monthly --force \\")
        for label in bad:
            print("        --month %s \\" % label)
    print()
    print("Refetching %d month(s) at the default 1,000 costs about $%.2f."
          % (len(bad), len(bad) * DEFAULT_MAX_ITEMS * COST_PER_POST))
    return 1


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
    print("          ranking, de-duplication, file writing, window enforcement,")
    print("          coverage measurement, and that a saved post loads back into")
    print("          XPost. Also proven live earlier: auth, run creation, polling,")
    print("          date translation and language.")
    print()
    print("  NOT proven offline: that X honours since:/until: under sort=%s, or"
          % SORT)
    print("          that minimumFavorites=%d leaves a pool big enough to span a"
          % DEFAULT_MIN_FAVORITES)
    print("          month. Both need one paid run, and both are checked")
    print("          automatically once it finishes. Do the cheap one first:")
    print("              python -m apify.fetch_monthly --month 2026-08 "
          "--max-items 200")
    print("          ~%d posts, about $%.2f. Then read the two lines it prints:"
          % (200, 200 * COST_PER_POST))
    print("          'window: N in, 0 out' means the fix holds; a coverage well")
    print("          under 100% means raise --min-favorites. Check disease_counts")
    print("          covers more than COVID before committing to 36 months.")
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

    if args.verify:
        return _verify(args.out_dir, windows)

    if args.dry_run:
        return _dry_run(windows, args.max_items, args.min_favorites)

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
            # Skipping protects paid data, but only if the file is right - use
            # --verify to check what is on disk actually holds the month it names.
            print("%s  already fetched, skipping (--force to redo, --verify to "
                  "check it)" % label, file=sys.stderr)
            continue

        print("%s  %s -> %s" % (label, start, end), file=sys.stderr)

        def on_poll(status, waited, _label=label):
            print("      ... %s (%ds)" % (status.lower(), waited), file=sys.stderr)

        def on_group(slugs, share, _label=label):
            print("  [%s] up to %d posts" % (", ".join(slugs), share),
                  file=sys.stderr)

        try:
            posts, stats = fetch_month(label, start, end, args.max_items,
                                       on_poll=on_poll, on_group=on_group,
                                       min_favorites=args.min_favorites)
        except ApifyError as e:
            print("error: %s" % e, file=sys.stderr)
            if total_billed:
                print("stopped after %d posts billed (about $%.2f)."
                      % (total_billed, total_billed * COST_PER_POST),
                      file=sys.stderr)
            return 1

        total_billed += stats["billed"]

        # Refuse to write a month the window did not actually produce. Saving it
        # would be worse than failing: main() skips months whose file exists, so
        # an empty or wrong-month file is preserved by every later rerun - which
        # is how 36 bad files survived to be discovered only after $14.28 was
        # spent. Same reasoning as the empty-dataset error in client.py.
        broken = _window_failure(label, stats)
        if broken:
            print("     %s" % broken, file=sys.stderr)
            print("     Not saving %s - a wrong file here would be skipped by "
                  "every rerun." % label, file=sys.stderr)
            print("stopped after %d posts billed (about $%.2f)."
                  % (total_billed, total_billed * COST_PER_POST),
                  file=sys.stderr)
            return 1

        total_kept += len(posts)
        saved = save_month(args.out_dir, label, start, end, posts,
                           args.max_items, stats, args.min_favorites)
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
        print("     window: %d in, %d out, %d undated; spans %.0f%% of the month "
              "over %d days"
              % (stats["in_window"], stats["out_of_window"], stats["undated"],
                 100 * stats["coverage"], stats["days_present"]),
              file=sys.stderr)
        # Silent in the run that wasted $14.28. Said at the point where stopping
        # is still worth something. The harder failure aborts above instead.
        if stats["out_of_window"] or stats["undated"]:
            print("     note: dropped %d post(s) X returned from outside %s."
                  % (stats["out_of_window"] + stats["undated"], label),
                  file=sys.stderr)
        if stats["coverage"] < MIN_WINDOW_COVERAGE:
            print("     WARNING: these posts span only %.0f%% of %s. sort=Latest "
                  "fills from the end of the window backwards, so raise "
                  "--min-favorites above %d to thin the pool and reach further "
                  "back." % (100 * stats["coverage"], label, args.min_favorites),
                  file=sys.stderr)

    print(file=sys.stderr)
    print("Done. %d posts kept, %d billed, about $%.2f."
          % (total_kept, total_billed, total_billed * COST_PER_POST),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
