"""Apify REST client for the apidojo/tweet-scraper Actor, stdlib only.

No apify-client dependency: the rest of this backend fetches posts with urllib and
main_api/requirements.txt is already carrying far more than it needs, so this
follows the same rule.

Uses the async run-then-poll path rather than run-sync-get-dataset-items. The sync
endpoint has a 300-second ceiling, and a run that is cut short after being paid for
is a worse failure than a slightly longer client.

    from apify.client import run_actor, ApifyError

    items = run_actor({"searchTerms": [...], "maxItems": 1000})

Needs APIFY_TOKEN in backend/.env (console.apify.com -> Settings -> Integrations).
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

__all__ = ["run_actor", "ApifyError"]

ACTOR_ID = "apidojo~tweet-scraper"
API_ROOT = "https://api.apify.com/v2"

# Apify reports these while the run is still going; anything else is terminal.
RUNNING_STATES = {"READY", "RUNNING"}

POLL_SECONDS = 5
POLL_TIMEOUT = 1800          # 30 min; a 1000-post month should take far less
DATASET_PAGE = 1000


class ApifyError(RuntimeError):
    """Apify rejected the request, or the Actor run did not succeed."""


def _token() -> str:
    token = os.getenv("APIFY_TOKEN")
    if not token:
        raise ApifyError(
            "APIFY_TOKEN is not set. Get one from "
            "https://console.apify.com/settings/integrations and add it to "
            "backend/.env as APIFY_TOKEN=..."
        )
    return token


def _request(url: str, payload: dict | None = None, timeout: int = 60) -> dict:
    """GET, or POST when `payload` is given. Returns the decoded JSON body."""
    data = None
    headers = {
        "Authorization": "Bearer %s" % _token(),
        "Accept": "application/json",
        "User-Agent": "vax-sentiment-research/1.0",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        if e.code == 401:
            raise ApifyError(
                "401 Unauthorized - APIFY_TOKEN is wrong or revoked.") from e
        if e.code == 402:
            raise ApifyError(
                "402 Payment Required - the Apify account is out of credit. The "
                "free tier allows 5 runs a month capped at 10 items each."
            ) from e
        if e.code == 404:
            raise ApifyError(
                "404 Not Found - %s. Check the actor id and run id." % url) from e
        if e.code == 429:
            raise ApifyError(
                "429 Rate limited by Apify - wait and retry.") from e
        raise ApifyError("HTTP %s from Apify: %s" % (e.code, detail)) from e
    except urllib.error.URLError as e:
        raise ApifyError("Could not reach Apify: %s" % e.reason) from e


def _start(actor_input: dict) -> dict:
    """Kick off a run; returns Apify's run object."""
    url = "%s/actors/%s/runs" % (API_ROOT, ACTOR_ID)
    return (_request(url, payload=actor_input) or {}).get("data") or {}


def _wait(run_id: str, on_poll=None) -> dict:
    """Block until the run leaves READY/RUNNING, then return the run object."""
    url = "%s/actor-runs/%s" % (API_ROOT, run_id)
    waited = 0
    while True:
        run = (_request(url) or {}).get("data") or {}
        status = run.get("status")
        if status not in RUNNING_STATES:
            return run
        if waited >= POLL_TIMEOUT:
            raise ApifyError(
                "Run %s still %s after %d seconds. It may still finish - check "
                "https://console.apify.com/actors/runs/%s before re-running, so "
                "you do not pay for it twice." % (run_id, status, waited, run_id))
        if on_poll:
            on_poll(status, waited)
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS


def _dataset_items(dataset_id: str) -> list[dict]:
    """Page the whole dataset out. Apify caps a page, so loop until short."""
    items: list[dict] = []
    offset = 0
    while True:
        qs = urllib.parse.urlencode(
            {"offset": offset, "limit": DATASET_PAGE, "format": "json"})
        url = "%s/datasets/%s/items?%s" % (API_ROOT, dataset_id, qs)
        page = _request(url)
        # This endpoint returns a bare JSON array, not the usual {"data": ...}.
        if not isinstance(page, list):
            page = page.get("items") or []
        items.extend(page)
        if len(page) < DATASET_PAGE:
            return items
        offset += len(page)


def run_actor(actor_input: dict, on_poll=None) -> list[dict]:
    """Run the Actor to completion and return its dataset items.

    `on_poll(status, seconds)` is called between polls so a CLI can show that
    something is happening during a multi-minute run.
    """
    run = _start(actor_input)
    run_id = run.get("id")
    if not run_id:
        raise ApifyError("Apify did not return a run id: %r" % run)

    run = _wait(run_id, on_poll=on_poll)
    status = run.get("status")
    if status != "SUCCEEDED":
        raise ApifyError(
            "Actor run %s finished as %s. See "
            "https://console.apify.com/actors/runs/%s" % (run_id, status, run_id))

    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        raise ApifyError("Run %s succeeded but exposed no dataset." % run_id)

    items = _dataset_items(dataset_id)
    if not items:
        # The Actor reports SUCCEEDED even when it refuses to do any work - a
        # plan limit, or a query X would not answer. Treating that as "this month
        # was quiet" writes an empty file and, because the CLI skips months it
        # has already written, loses that month permanently. So it is an error.
        raise ApifyError(
            "Run %s returned no posts. The Actor reports SUCCEEDED even when it "
            "refuses to run, so read the log: %s -- status message: %s. Usual "
            "causes: the ACTOR's own free-tier gate - apidojo caps FREE-plan "
            "accounts at 5 runs a month of 10 items each, by plan tier, so "
            "unspent Apify credit does not lift it; a query over X's "
            "512-character limit, which X "
            "answers with zero results rather than an error; or a start/end "
            "window with nothing in it."
            % (run_id, "https://console.apify.com/actors/runs/" + run_id,
               (run.get("statusMessage") or "none").strip() or "none"))
    return items
