"""Offline proof that the Apify collector works, short of X itself.

    python -m unittest apify.selftest -v

stdlib unittest, no pytest, nothing to install. Every Actor call is stubbed, so
this needs no APIFY_TOKEN, touches no network and spends nothing.

What it cannot prove: that the four queries return posts from X. That needs a paid
run. Everything downstream of X - normalising, tagging, ranking, de-duplicating,
writing files, loading into XPost - is proven here, as are the failure modes that
actually bit during development.
"""

import json
import os
import shutil
import tempfile
import unittest
from datetime import date

from . import client, fetch_monthly
from .client import ApifyError
# Import these by name, not as `from . import normalise`: the package __init__
# re-exports a FUNCTION called normalise, which shadows the module of the same
# name depending on import order.
from .normalise import BACKEND, engagement
from .normalise import normalise as to_post
from .diseases import (APPENDED_CHARS, DISEASES, QUERY_BUDGET, X_QUERY_LIMIT,
                       QueryTooLong, query_groups, tag)

# Shaped after the Actor's own published sample item, so the mapping is tested
# against the documented payload rather than something invented to pass.
SAMPLE = {
    "type": "tweet",
    "id": "1728108619189874825",
    "url": "https://x.com/elonmusk/status/1728108619189874825",
    "text": "More than 10 per human on average",
    "retweetCount": 11311, "replyCount": 6526, "likeCount": 104121,
    "quoteCount": 2915, "bookmarkCount": 702,
    "createdAt": "Fri Nov 24 17:49:36 +0000 2023",
    "lang": "en", "quoteId": "1728107610631729415",
    "isReply": False, "isRetweet": False, "isQuote": True,
    "source": "Twitter for Android",
    "author": {"type": "user", "id": "44196397", "userName": "elonmusk",
               "name": "Elon Musk", "isVerified": True, "followers": 172669889},
}


def item(i, text="covid vaccine rollout", likes=None):
    """One Actor-shaped item, varying only what the tests care about."""
    out = dict(SAMPLE)
    out.update(id=str(i), text=text,
               likeCount=i if likes is None else likes,
               retweetCount=0, replyCount=0, quoteCount=0)
    return out


class QuerySafety(unittest.TestCase):
    """The failure that cost a paid run: a query X answers with silence."""

    def test_every_group_within_the_proven_budget(self):
        for slugs, query in query_groups():
            self.assertLessEqual(
                len(query), QUERY_BUDGET,
                "%s is %d chars, over the proven-safe budget of %d"
                % (slugs, len(query), QUERY_BUDGET))

    def test_every_group_within_x_hard_limit_once_apify_appends(self):
        for slugs, query in query_groups():
            self.assertLessEqual(len(query) + APPENDED_CHARS, X_QUERY_LIMIT,
                                 "%s would be truncated by X" % (slugs,))

    def test_all_nine_diseases_covered_exactly_once(self):
        covered = [s for slugs, _ in query_groups() for s in slugs]
        self.assertEqual(sorted(covered), sorted(DISEASES))
        self.assertEqual(len(covered), len(set(covered)), "a disease is duplicated")

    def test_queries_are_syntactically_balanced(self):
        for slugs, query in query_groups():
            self.assertEqual(query.count("("), query.count(")"), slugs)
            self.assertEqual(query.count('"') % 2, 0, slugs)

    def test_guard_raises_rather_than_shipping_an_overlong_query(self):
        # A budget that lets everything into one group must be refused, not sent.
        with self.assertRaises(QueryTooLong):
            query_groups(budget=5000)


class Contract(unittest.TestCase):
    """The normalised dict is what every other source in this backend emits."""

    def test_createdAt_parses_with_the_projects_own_parser(self):
        from models import parse_x_time
        parsed = parse_x_time(to_post(SAMPLE)["created_at"])
        self.assertIsNotNone(parsed, "the Actor's date format stopped parsing")
        self.assertIsNotNone(parsed.tzinfo, "date lost its timezone")
        self.assertEqual((parsed.year, parsed.month, parsed.day), (2023, 11, 24))

    def test_xpost_accepts_a_normalised_item(self):
        from models import XPost
        row = XPost.from_fetch(to_post(SAMPLE))
        self.assertEqual(row.id, SAMPLE["id"])
        self.assertEqual(row.likes, SAMPLE["likeCount"])
        self.assertEqual(row.backend, BACKEND)

    def test_views_is_none_not_zero(self):
        # The Actor supplies no view count. A 0 would read as "nobody saw this".
        self.assertIsNone(to_post(SAMPLE)["views"])

    def test_source_client_survives(self):
        # The official v2 API dropped `source`; this path still has it.
        self.assertEqual(to_post(SAMPLE)["source_client"],
                         "Twitter for Android")

    def test_engagement_excludes_views_and_bookmarks(self):
        self.assertEqual(engagement(to_post(SAMPLE)),
                         104121 + 11311 + 6526 + 2915)


class Tagging(unittest.TestCase):
    """Tags must agree with what the queries actually searched for."""

    def test_disease_term_needs_a_vaccine_word(self):
        self.assertEqual(tag("measles outbreak in the county"), [])
        self.assertEqual(tag("measles vaccination rates falling"), ["mmr"])

    def test_brand_names_stand_alone(self):
        self.assertEqual(tag("Gardasil saved lives"), ["hpv"])

    def test_ambiguous_initialisms_do_not_false_positive(self):
        self.assertEqual(tag("BCG is a great consulting firm"), [])
        self.assertEqual(tag("the BCG vaccine for tuberculosis"), ["tuberculosis"])

    def test_word_boundaries_hold(self):
        # "tb" inside "subtle", "hepa" inside "heparin"
        self.assertEqual(tag("a subtle reaction to the vaccine"), [])
        self.assertEqual(tag("heparin drip, got my vaccine too"), [])

    def test_a_post_can_match_several_diseases(self):
        self.assertEqual(tag("the MMR vaccine and the covid booster"),
                         ["covid19", "mmr"])


class Months(unittest.TestCase):
    FIXED = date(2026, 9, 29)

    def test_count_and_labels(self):
        ms = fetch_monthly.months(36, now=self.FIXED)
        self.assertEqual(len(ms), 36)
        self.assertEqual(ms[0][0], "2023-10")
        self.assertEqual(ms[-1][0], "2026-09")

    def test_windows_tile_without_gaps_or_overlaps(self):
        ms = fetch_monthly.months(36, now=self.FIXED)
        for earlier, later in zip(ms, ms[1:]):
            self.assertEqual(earlier[2], later[1])

    def test_current_month_does_not_run_into_the_future(self):
        ms = fetch_monthly.months(36, now=self.FIXED)
        self.assertEqual(ms[-1][2], self.FIXED.isoformat())

    def test_crosses_a_year_boundary(self):
        ms = fetch_monthly.months(4, now=date(2025, 2, 10))
        self.assertEqual([m[0] for m in ms],
                         ["2024-11", "2024-12", "2025-01", "2025-02"])


class Pipeline(unittest.TestCase):
    """Actor items in, ranked and tagged posts on disk, XPost out."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.calls = []
        self._real = fetch_monthly.run_actor
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.addCleanup(setattr, fetch_monthly, "run_actor", self._real)

    def stub(self, items_for_group):
        def fake(actor_input, on_poll=None):
            self.calls.append(actor_input)
            return items_for_group(len(self.calls) - 1)
        fetch_monthly.run_actor = fake

    def test_one_run_per_group_with_the_allocation_split(self):
        self.stub(lambda n: [item(n * 1000 + i) for i in range(5)])
        fetch_monthly.fetch_month("2026-08", "2026-08-01", "2026-09-01", 1000)
        self.assertEqual(len(self.calls), len(query_groups()))
        for sent in self.calls:
            self.assertEqual(sent["maxItems"], 1000 // len(query_groups()))

    def test_actor_input_uses_only_published_schema_fields(self):
        self.stub(lambda n: [item(n)])
        fetch_monthly.fetch_month("2026-08", "2026-08-01", "2026-09-01", 200)
        self.assertEqual(
            sorted(self.calls[0]),
            ["end", "maxItems", "searchTerms", "sort", "start", "tweetLanguage"])
        self.assertEqual(self.calls[0]["sort"], "Top")
        self.assertEqual(self.calls[0]["tweetLanguage"], "en")
        self.assertEqual(len(self.calls[0]["searchTerms"]), 1,
                         "one query per run - the Actor walks searchTerms "
                         "sequentially against one shared maxItems")

    def test_minimum_item_floor_is_respected(self):
        self.stub(lambda n: [item(n)])
        fetch_monthly.fetch_month("2026-08", "2026-08-01", "2026-09-01", 4)
        self.assertGreaterEqual(self.calls[0]["maxItems"], fetch_monthly.MIN_ITEMS)

    def test_floor_overshoot_is_reported_not_hidden(self):
        # --max-items 100 over 4 groups wants 25 each, but 50 is the Actor's
        # minimum, so 200 are fetched and billed while 100 are kept. That cost
        # the user real money before it was surfaced.
        n = len(query_groups())
        self.assertEqual(fetch_monthly.share_per_group(100, n),
                         fetch_monthly.MIN_ITEMS)
        self.assertEqual(fetch_monthly.effective_total(100, n),
                         fetch_monthly.MIN_ITEMS * n)
        warning = fetch_monthly._floor_warning(100, n)
        self.assertIsNotNone(warning, "overshoot must be warned about")
        self.assertIn(str(fetch_monthly.MIN_ITEMS * n), warning)

    def test_no_warning_when_the_allocation_clears_the_floor(self):
        n = len(query_groups())
        self.assertIsNone(fetch_monthly._floor_warning(1000, n))
        self.assertEqual(fetch_monthly.effective_total(1000, n), 1000)

    def test_billed_counts_every_post_the_actor_returned(self):
        # 3 kept after de-duplication, but 5 per group were returned and charged.
        self.stub(lambda n: [item(i) for i in range(5)])
        posts, stats = fetch_monthly.fetch_month(
            "2026-08", "2026-08-01", "2026-09-01", 1000)
        self.assertEqual(stats["billed"], 5 * len(query_groups()))
        self.assertLess(len(posts), stats["billed"],
                        "de-duplication should leave billed above kept here")
        # every billed post must be accounted for, not silently missing
        self.assertEqual(
            stats["billed"],
            stats["collected"] + stats["duplicates"] + stats["no_id"])
        self.assertEqual(stats["duplicates"], 5 * (len(query_groups()) - 1))

    def test_posts_are_ranked_by_engagement_and_tagged(self):
        self.stub(lambda n: [item(n * 100 + i, likes=i * 3) for i in range(5)])
        posts, _ = fetch_monthly.fetch_month("2026-08", "2026-08-01",
                                             "2026-09-01", 1000)
        scores = [engagement(p) for p in posts]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(posts[0]["month"], "2026-08")
        self.assertEqual(posts[0]["diseases"], ["covid19"])

    def test_a_post_returned_by_two_groups_is_stored_once(self):
        # proquad is both MMR and chickenpox, so overlap is real, not theoretical.
        self.stub(lambda n: [item(77, text="proquad vaccine")])
        posts, _ = fetch_monthly.fetch_month("2026-08", "2026-08-01",
                                             "2026-09-01", 1000)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["diseases"], ["chickenpox", "mmr"])

    def test_month_is_written_and_reloads_into_xpost(self):
        from models import XPost
        self.stub(lambda n: [item(n * 100 + i) for i in range(10)])
        with _quiet():
            rc = fetch_monthly.main(["--month", "2026-08", "--max-items", "200",
                                     "--out-dir", self.dir])
        self.assertEqual(rc, 0)

        path = os.path.join(self.dir, "apify_vax_2026-08.json")
        self.assertTrue(os.path.exists(path), "no file written")
        with open(path, encoding="utf-8") as fh:
            saved = json.load(fh)

        self.assertEqual(saved["month"], "2026-08")
        self.assertEqual(saved["posts_kept"], len(saved["posts"]))
        self.assertGreater(saved["posts_kept"], 0)
        # Cost must follow what the Actor returned, not what survived the cut.
        self.assertGreaterEqual(saved["posts_billed"], saved["posts_kept"])
        self.assertAlmostEqual(
            saved["estimated_cost_usd"],
            round(saved["posts_billed"] * fetch_monthly.COST_PER_POST, 4))
        self.assertEqual(len(saved["queries"]), len(query_groups()))
        self.assertEqual(saved["ranked_by"], "likes + reposts + replies + quotes")
        # The whole point of writing files: they load back into the database model.
        XPost.from_fetch(saved["posts"][0])

    def test_non_ascii_text_is_stored_readably(self):
        self.stub(lambda n: [item(n, text="vacuna contra el covid — café")])
        with _quiet():
            fetch_monthly.main(["--month", "2026-08", "--max-items", "200",
                                "--out-dir", self.dir])
        with open(os.path.join(self.dir, "apify_vax_2026-08.json"),
                  encoding="utf-8") as fh:
            raw = fh.read()
        self.assertIn("café", raw)
        self.assertNotIn(chr(92) + "u00e9", raw)


class FailureModes(unittest.TestCase):
    """The ones that actually bit, not hypotheticals."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self._real = fetch_monthly.run_actor
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.addCleanup(setattr, fetch_monthly, "run_actor", self._real)

    def test_empty_dataset_raises_instead_of_looking_like_success(self):
        # The Actor reports SUCCEEDED even when a plan limit stops it dead.
        real = (client._start, client._wait, client._dataset_items)
        self.addCleanup(lambda: setattr_many(client, real))
        client._start = lambda i: {"id": "RUN1"}
        client._wait = lambda r, on_poll=None: {
            "status": "SUCCEEDED", "defaultDatasetId": "DS1",
            "statusMessage": "Monthly run limit exceeded per user."}
        client._dataset_items = lambda d: []
        with self.assertRaises(ApifyError) as ctx:
            client.run_actor({})
        self.assertIn("Monthly run limit exceeded", str(ctx.exception))

    def test_a_failed_month_leaves_no_file_so_resume_retries_it(self):
        def boom(actor_input, on_poll=None):
            raise ApifyError("Run RUN1 returned no posts.")
        fetch_monthly.run_actor = boom
        with _quiet():
            rc = fetch_monthly.main(["--month", "2026-08", "--max-items", "200",
                                     "--out-dir", self.dir])
        self.assertEqual(rc, 1, "a failed month must exit non-zero")
        self.assertEqual(os.listdir(self.dir), [],
                         "an empty month was recorded as done and would be "
                         "skipped forever")

    def test_already_fetched_month_is_skipped_without_a_network_call(self):
        fetch_monthly.run_actor = lambda *a, **k: [item(1)]
        with _quiet():
            fetch_monthly.main(["--month", "2026-08", "--max-items", "200",
                                "--out-dir", self.dir])

        def never(*a, **k):
            raise AssertionError("re-fetched a month already on disk")
        fetch_monthly.run_actor = never
        with _quiet():
            rc = fetch_monthly.main(["--month", "2026-08", "--max-items", "200",
                                     "--out-dir", self.dir])
        self.assertEqual(rc, 0)

    def test_force_refetches(self):
        fetch_monthly.run_actor = lambda *a, **k: [item(1)]
        with _quiet():
            fetch_monthly.main(["--month", "2026-08", "--max-items", "200",
                                "--out-dir", self.dir])
        calls = []
        fetch_monthly.run_actor = lambda i, on_poll=None: (calls.append(1)
                                                           or [item(2)])
        with _quiet():
            fetch_monthly.main(["--month", "2026-08", "--max-items", "200",
                                "--out-dir", self.dir, "--force"])
        self.assertTrue(calls, "--force did not re-fetch")

    def test_missing_token_says_where_to_get_one(self):
        old = os.environ.pop("APIFY_TOKEN", None)
        self.addCleanup(lambda: os.environ.__setitem__("APIFY_TOKEN", old)
                        if old else None)
        with self.assertRaises(ApifyError) as ctx:
            client._token()
        self.assertIn("console.apify.com", str(ctx.exception))


def setattr_many(module, triple):
    module._start, module._wait, module._dataset_items = triple


class _quiet:
    """Silence the CLI's progress output during tests."""

    def __enter__(self):
        import contextlib, io as _io
        self._out = contextlib.redirect_stdout(_io.StringIO())
        self._err = contextlib.redirect_stderr(_io.StringIO())
        self._out.__enter__()
        self._err.__enter__()

    def __exit__(self, *exc):
        self._err.__exit__(*exc)
        self._out.__exit__(*exc)
        return False


if __name__ == "__main__":
    unittest.main()
