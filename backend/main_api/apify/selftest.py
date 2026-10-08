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


# Inside the 2026-08 window the Pipeline tests use. SAMPLE's own createdAt is from
# 2023 and stays that way - it is the Actor's documented payload - but a post that
# fetch_month is asked to file under 2026-08 has to be from 2026-08 or it is now
# dropped as out-of-window, which is the point of the window check.
IN_WINDOW = "Wed Aug 12 10:00:00 +0000 2026"


def item(i, text="covid vaccine rollout", likes=None, created=IN_WINDOW):
    """One Actor-shaped item, varying only what the tests care about."""
    out = dict(SAMPLE)
    out.update(id=str(i), text=text,
               likeCount=i if likes is None else likes,
               retweetCount=0, replyCount=0, quoteCount=0,
               createdAt=created)
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

    def test_an_empty_current_month_is_dropped(self):
        # Run on the 1st and the current month clamps to start == end. The Actor
        # returns nothing for that, client.py calls an empty run an error, and the
        # whole command would fail on its last month after paying for the rest.
        ms = fetch_monthly.months(3, now=date(2026, 10, 1))
        self.assertEqual([m[0] for m in ms], ["2026-08", "2026-09"])
        for _label, start, end in ms:
            self.assertLess(start, end)

    def test_no_window_is_ever_empty(self):
        for day in (1, 2, 15, 28):
            for month in (1, 6, 12):
                for _label, start, end in fetch_monthly.months(
                        6, now=date(2026, month, day)):
                    self.assertLess(start, end, "empty window at %04d-%02d-%02d"
                                    % (2026, month, day))


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
            ["end", "maxItems", "minimumFavorites", "searchTerms", "sort",
             "start", "tweetLanguage"])
        self.assertEqual(self.calls[0]["tweetLanguage"], "en")
        self.assertEqual(len(self.calls[0]["searchTerms"]), 1,
                         "one query per run - the Actor walks searchTerms "
                         "sequentially against one shared maxItems")

    def test_sort_is_latest_because_top_ignores_the_date_window(self):
        # The regression that cost $14.28: sort="Top" made X ignore until: and
        # return currently-popular posts for every month asked for. Asserted by
        # name so a future "but Top ranks by engagement" change has to confront
        # this test and the history in the module docstring.
        self.stub(lambda n: [item(n)])
        fetch_monthly.fetch_month("2026-08", "2026-08-01", "2026-09-01", 200)
        self.assertEqual(self.calls[0]["sort"], "Latest")
        self.assertNotEqual(self.calls[0]["sort"], "Top")
        self.assertEqual(fetch_monthly.SORT, "Latest")

    def test_engagement_floor_is_sent_and_configurable(self):
        self.stub(lambda n: [item(n)])
        fetch_monthly.fetch_month("2026-08", "2026-08-01", "2026-09-01", 200)
        self.assertEqual(self.calls[0]["minimumFavorites"],
                         fetch_monthly.DEFAULT_MIN_FAVORITES)
        self.calls.clear()
        fetch_monthly.fetch_month("2026-08", "2026-08-01", "2026-09-01", 200,
                                  min_favorites=500)
        self.assertEqual(self.calls[0]["minimumFavorites"], 500)

    def test_posts_outside_the_month_are_dropped_and_counted(self):
        # Exactly the shape of the failure: the window says August 2026, X hands
        # back February 2025. Those posts must not be filed under 2026-08.
        def mixed(n):
            return [item(n * 100 + 1),
                    item(n * 100 + 2, created="Fri Feb 14 19:40:10 +0000 2025"),
                    item(n * 100 + 3, created="Tue Sep 15 08:00:00 +0000 2026")]
        self.stub(mixed)
        posts, stats = fetch_monthly.fetch_month(
            "2026-08", "2026-08-01", "2026-09-01", 1000)
        groups = len(query_groups())
        self.assertEqual(stats["out_of_window"], 2 * groups)
        self.assertEqual(stats["in_window"], groups)
        self.assertEqual(len(posts), groups)
        self.assertEqual(stats["collected"],
                         stats["in_window"] + stats["out_of_window"]
                         + stats["undated"])
        for post in posts:
            self.assertEqual(fetch_monthly.created_on(post).month, 8)

    def test_end_of_window_is_exclusive(self):
        # months() tiles with an exclusive end, so the 1st of the next month
        # belongs to the next file, not this one.
        self.stub(lambda n: [item(n, created="Tue Sep 01 00:00:01 +0000 2026")])
        posts, stats = fetch_monthly.fetch_month(
            "2026-08", "2026-08-01", "2026-09-01", 1000)
        self.assertEqual(posts, [])
        self.assertEqual(stats["in_window"], 0)

    def test_unparseable_date_is_dropped_not_filed(self):
        self.stub(lambda n: [item(n, created="not a date")])
        posts, stats = fetch_monthly.fetch_month(
            "2026-08", "2026-08-01", "2026-09-01", 1000)
        self.assertEqual(posts, [])
        self.assertEqual(stats["undated"], len(query_groups()))

    def test_coverage_reports_how_much_of_the_month_was_reached(self):
        # sort="Latest" fills from the end of the window backwards, so posts
        # bunched in the last days are the expected symptom of too low a floor.
        tail = ["Sat Aug 29 10:00:00 +0000 2026", "Sun Aug 30 10:00:00 +0000 2026",
                "Mon Aug 31 10:00:00 +0000 2026"]
        self.stub(lambda n: [item(n * 100 + i, created=c)
                             for i, c in enumerate(tail)])
        _posts, stats = fetch_monthly.fetch_month(
            "2026-08", "2026-08-01", "2026-09-01", 1000)
        self.assertLess(stats["coverage"], fetch_monthly.MIN_WINDOW_COVERAGE)
        self.assertEqual(stats["days_present"], 3)

        self.calls.clear()
        spread = ["Sat Aug 01 10:00:00 +0000 2026",
                  "Mon Aug 31 10:00:00 +0000 2026"]
        self.stub(lambda n: [item(n * 100 + i, created=c)
                             for i, c in enumerate(spread)])
        _posts, stats = fetch_monthly.fetch_month(
            "2026-08", "2026-08-01", "2026-09-01", 1000)
        self.assertEqual(stats["coverage"], 1.0)

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
        # The audit a reader needs to trust the filename. Recorded, not implied.
        self.assertEqual(saved["sort_requested"], "Latest")
        self.assertEqual(saved["posts_out_of_window"], 0)
        self.assertEqual(saved["posts_undated"], 0)
        self.assertEqual(saved["posts_in_window"], saved["posts_kept"])
        self.assertIn("window_coverage", saved)
        self.assertEqual(saved["min_favorites"],
                         fetch_monthly.DEFAULT_MIN_FAVORITES)
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

    @staticmethod
    def _saved_post(i, created):
        """A post as fetch_month would have left it: normalised, tagged, filed."""
        post = to_post(item(i, created=created))
        post["month"] = "2026-08"
        post["diseases"] = ["covid19"]
        return post

    def test_a_month_the_window_did_not_produce_is_not_written(self):
        # The exact 2026-09 shape: ask for August, get September. Writing it would
        # be worse than failing - a rerun skips months whose file exists, so the
        # wrong month would survive every retry.
        fetch_monthly.run_actor = lambda *a, **k: [
            item(n, created="Tue Sep 15 08:00:00 +0000 2026") for n in range(5)]
        with _quiet():
            rc = fetch_monthly.main(["--month", "2026-08", "--max-items", "200",
                                     "--out-dir", self.dir])
        self.assertEqual(rc, 1, "a month X did not window must exit non-zero")
        self.assertEqual(os.listdir(self.dir), [],
                         "a wrong month was written and would be skipped forever")

    def test_a_mostly_out_of_window_month_is_not_written(self):
        # Partial leak: 1 in, 4 out. The window is being treated as a suggestion.
        def mixed(*a, **k):
            return ([item(1, created="Sat Aug 15 10:00:00 +0000 2026")]
                    + [item(10 + n, created="Fri Feb 14 19:40:10 +0000 2025")
                       for n in range(4)])
        fetch_monthly.run_actor = mixed
        with _quiet():
            rc = fetch_monthly.main(["--month", "2026-08", "--max-items", "200",
                                     "--out-dir", self.dir])
        self.assertEqual(rc, 1)
        self.assertEqual(os.listdir(self.dir), [])

    def test_a_few_stray_posts_are_dropped_but_the_month_is_kept(self):
        # Mostly good: strays are dropped, the month still saves. Being strict
        # here would throw away a usable month over a handful of posts.
        def mostly(*a, **k):
            return ([item(n, created="Sat Aug %02d 10:00:00 +0000 2026" % (n + 1))
                     for n in range(1, 9)]
                    + [item(99, created="Fri Feb 14 19:40:10 +0000 2025")])
        fetch_monthly.run_actor = mostly
        with _quiet():
            rc = fetch_monthly.main(["--month", "2026-08", "--max-items", "200",
                                     "--out-dir", self.dir])
        self.assertEqual(rc, 0)
        with open(os.path.join(self.dir, "apify_vax_2026-08.json"),
                  encoding="utf-8") as fh:
            saved = json.load(fh)
        self.assertEqual(saved["posts_out_of_window"], 1)
        self.assertEqual(saved["posts_kept"], 8)
        for post in saved["posts"]:
            self.assertIn("Aug", post["created_at"])

    def test_verify_flags_a_file_that_is_not_the_month_it_names(self):
        # The audit for the 36 files already on disk. A rerun skips months whose
        # file exists, so without this a wrong month is preserved forever.
        good = os.path.join(self.dir, "apify_vax_2026-08.json")
        fetch_monthly.save_month(
            self.dir, "2026-08", "2026-08-01", "2026-09-01",
            [self._saved_post(1, "Sat Aug 01 10:00:00 +0000 2026"),
             self._saved_post(2, "Mon Aug 31 10:00:00 +0000 2026")],
            200, {"billed": 2, "duplicates": 0, "no_id": 0, "collected": 2,
                  "out_of_window": 0, "undated": 0, "in_window": 2,
                  "coverage": 1.0, "days_present": 2})
        self.assertTrue(os.path.exists(good))
        with _quiet():
            self.assertEqual(
                fetch_monthly._verify(self.dir,
                                      [("2026-08", "2026-08-01", "2026-09-01")]),
                0)

        # Now the real-world case: posts from the wrong year under 2026-08.
        fetch_monthly.save_month(
            self.dir, "2026-08", "2026-08-01", "2026-09-01",
            [self._saved_post(3, "Fri Feb 14 19:40:10 +0000 2025")],
            200, {"billed": 1, "duplicates": 0, "no_id": 0, "collected": 1,
                  "out_of_window": 0, "undated": 0, "in_window": 1,
                  "coverage": 1.0, "days_present": 1})
        with _quiet():
            self.assertEqual(
                fetch_monthly._verify(self.dir,
                                      [("2026-08", "2026-08-01", "2026-09-01")]),
                1, "a file full of the wrong month must fail the audit")

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
