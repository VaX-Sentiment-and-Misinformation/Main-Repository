#!/usr/bin/env python3
"""
xscrape.py - fetch public X (Twitter) posts by ID. No API key, no login.

Backends (tried in order by default):
  1. fxtwitter  - api.fxtwitter.com/2/status/{id}   (public, ~1000 req/min per IP)
  2. syndication - cdn.syndication.twimg.com/tweet-result  (X's own embed endpoint)

Stdlib only. Python 3.8+.

Usage:
  python xscrape.py 20 1234567890123456789
  python xscrape.py --from-file ids.txt --out posts.jsonl --csv posts.csv
  python xscrape.py https://x.com/jack/status/20 --pretty
"""

import argparse
import csv
import datetime
import json
import math
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
FX = "https://api.fxtwitter.com/2/status/{id}"
SYND = "https://cdn.syndication.twimg.com/tweet-result?id={id}&token={token}&lang=en"
ID_RE = re.compile(r"(\d{5,25})")


# ---------- helpers ----------

def parse_id(raw):
    """Accept a bare ID, an x.com/twitter.com URL, or junk with an ID in it."""
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        return None
    m = re.search(r"status(?:es)?/(\d+)", raw)
    if m:
        return m.group(1)
    if raw.isdigit():          # bare ID, any length (jack's first post is just "20")
        return raw
    m = ID_RE.search(raw)      # otherwise dig one out of surrounding junk
    return m.group(1) if m else None


ID_COL_HINTS = ("tweet_id", "post_id", "status_id", "tweetid", "postid", "id_str", "id", "url", "link")


def _pick_column(header):
    """Find the most likely ID column in a CSV header row."""
    lowered = [h.strip().lower() for h in header]
    for hint in ID_COL_HINTS:
        if hint in lowered:
            return lowered.index(hint)
    return None


def read_ids(path, id_column=None, limit=0, offset=0):
    """Stream IDs out of a CSV or plain text file.

    Streams line by line and stops as soon as the limit is hit, so a
    600k-row CSV costs nothing extra when you only want the first 10k.
    Dedupes as it goes; limit and offset apply to unique valid IDs.
    """
    ids, seen, skipped, unparseable = [], set(), 0, 0
    is_csv = path.lower().endswith((".csv", ".tsv"))
    delim = "\t" if path.lower().endswith(".tsv") else ","
    col = None

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        if is_csv:
            reader = csv.reader(f, delimiter=delim)
            try:
                header = next(reader)
            except StopIteration:
                return []

            if id_column is not None:
                if id_column.isdigit():
                    col = int(id_column)
                else:
                    lowered = [h.strip().lower() for h in header]
                    if id_column.lower() not in lowered:
                        raise SystemExit("column %r not found. header is: %s"
                                         % (id_column, ", ".join(header)))
                    col = lowered.index(id_column.lower())
            else:
                col = _pick_column(header)
                if col is not None:
                    print("using CSV column %r" % header[col], file=sys.stderr)

            if col is None:
                # no header we recognise, so treat row 1 as data and scan whole rows
                print("no ID column detected, scanning every field "
                      "(pass --id-column to be explicit)", file=sys.stderr)
                rows = [header] + list(reader)
                reader = iter(rows)

            for row in reader:
                if not row:
                    continue
                cell = row[col] if (col is not None and col < len(row)) else " ".join(row)
                tid = parse_id(cell)
                if not tid:
                    unparseable += 1
                    continue
                if tid in seen:
                    continue
                seen.add(tid)
                if skipped < offset:
                    skipped += 1
                    continue
                ids.append(tid)
                if limit and len(ids) >= limit:
                    break
        else:
            for line in f:
                tid = parse_id(line)
                if not tid or tid in seen:
                    continue
                seen.add(tid)
                if skipped < offset:
                    skipped += 1
                    continue
                ids.append(tid)
                if limit and len(ids) >= limit:
                    break

    if unparseable:
        print("warning: %d rows had no usable ID in that column "
              "(scientific notation? wrong column?)" % unparseable, file=sys.stderr)
    return ids


def _base36(x):
    """Port of JS Number.prototype.toString(36) for positive floats."""
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    ip, frac = int(x), x - int(x)
    if ip == 0:
        head = "0"
    else:
        head = ""
        while ip:
            head = digits[ip % 36] + head
            ip //= 36
    if frac <= 0:
        return head
    tail = ""
    for _ in range(20):
        frac *= 36
        d = int(frac)
        tail += digits[d]
        frac -= d
        if frac == 0:
            break
    return head + "." + tail


def synd_token(tweet_id):
    """Same token derivation X's own embed widget uses."""
    return re.sub(r"(0+|\.)", "", _base36((int(tweet_id) / 1e15) * math.pi))


def get_json(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# ---------- backends ----------

def via_fxtwitter(tweet_id):
    data = get_json(FX.format(id=tweet_id))
    if data.get("code") != 200:
        raise LookupError(data.get("message") or "code %s" % data.get("code"))
    s = data.get("status") or {}
    if s.get("type") == "tombstone":
        raise LookupError(s.get("reason") or "unavailable")

    a = s.get("author") or {}
    media = (s.get("media") or {}).get("all") or []
    reply = s.get("replying_to") or {}

    return {
        "id": s.get("id"),
        "url": s.get("url"),
        "created_at": s.get("created_at"),
        "created_timestamp": s.get("created_timestamp"),
        "text": s.get("text"),
        "lang": s.get("lang"),
        "author_name": a.get("name"),
        "author_handle": a.get("screen_name"),
        "author_id": a.get("id"),
        "author_followers": a.get("followers"),
        "replies": s.get("replies"),
        "reposts": s.get("reposts"),
        "likes": s.get("likes"),
        "quotes": s.get("quotes"),
        "views": s.get("views"),
        "bookmarks": s.get("bookmarks"),
        "is_reply_to": reply.get("status"),
        "reply_to_handle": reply.get("screen_name"),
        "is_quote": bool(s.get("quote")),
        "quoted_id": (s.get("quote") or {}).get("id"),
        "possibly_sensitive": s.get("possibly_sensitive"),
        "source_client": s.get("source"),
        "media_count": len(media),
        "media_urls": [m.get("url") for m in media if m.get("url")],
        "has_poll": bool(s.get("poll")),
        "has_community_note": bool(s.get("community_note")),
        "_backend": "fxtwitter",
    }


def via_syndication(tweet_id):
    data = get_json(SYND.format(id=tweet_id, token=synd_token(tweet_id)))
    if not data or "text" not in data:
        raise LookupError("empty syndication response")

    u = data.get("user") or {}
    media = data.get("mediaDetails") or []
    return {
        "id": data.get("id_str") or str(tweet_id),
        "url": "https://x.com/%s/status/%s" % (u.get("screen_name", "i"), tweet_id),
        "created_at": data.get("created_at"),
        "created_timestamp": None,
        "text": data.get("text"),
        "lang": data.get("lang"),
        "author_name": u.get("name"),
        "author_handle": u.get("screen_name"),
        "author_id": u.get("id_str"),
        "author_followers": None,
        "replies": data.get("conversation_count"),
        "reposts": None,
        "likes": data.get("favorite_count"),
        "quotes": None,
        "views": None,
        "bookmarks": None,
        "is_reply_to": data.get("in_reply_to_status_id_str"),
        "reply_to_handle": data.get("in_reply_to_screen_name"),
        "is_quote": bool(data.get("quoted_tweet")),
        "quoted_id": (data.get("quoted_tweet") or {}).get("id_str"),
        "possibly_sensitive": data.get("possibly_sensitive"),
        "source_client": None,
        "media_count": len(media),
        "media_urls": [m.get("media_url_https") for m in media if m.get("media_url_https")],
        "has_poll": bool(data.get("card")),
        "has_community_note": None,
        "_backend": "syndication",
    }


BACKENDS = {"fxtwitter": via_fxtwitter, "syndication": via_syndication}


# ---------- fetching ----------

TWITTER_EPOCH_MS = 1288834974657  # 2010-11-04, when snowflake IDs began


def snowflake_date(tweet_id):
    """Decode a post's creation time from its ID. None for pre-2010 IDs."""
    n = int(tweet_id)
    if n < 29700859247:  # sequential era, no timestamp encoded
        return None
    ms = (n >> 22) + TWITTER_EPOCH_MS
    try:
        return datetime.datetime.fromtimestamp(ms / 1000.0, datetime.timezone.utc)
    except (ValueError, OSError, OverflowError):
        return None


def dry_run(ids):
    """Validate IDs offline and report anything that looks mangled."""
    now = datetime.datetime.now(datetime.timezone.utc)
    lengths, dated, undecodable, future, ancient = {}, [], [], [], []
    rounded = [t for t in ids if len(t) >= 18 and t.endswith("0000")]
    # float64 spacing at 1.7e18 is 256, so a genuine ID lands exactly on a
    # representable float only ~0.45% of the time. An ID that has been through
    # a float (pandas read_csv, json parsing, JS) is float-exact 100% of the time.
    big = [t for t in ids if len(t) >= 18]
    float_exact = [t for t in big if int(float(t)) == int(t)]

    for t in ids:
        lengths[len(t)] = lengths.get(len(t), 0) + 1
        d = snowflake_date(t)
        if d is None:
            undecodable.append(t)
        elif d > now:
            future.append((t, d))
        elif d.year < 2006:
            ancient.append((t, d))
        else:
            dated.append((t, d))

    print("\n=== dry run: %d unique IDs ===" % len(ids))
    print("\nID length distribution:")
    for L in sorted(lengths):
        flag = "" if L in (18, 19) else "   <-- suspicious, real post IDs are 18-19 digits"
        print("  %2d digits: %6d%s" % (L, lengths[L], flag))

    if dated:
        dates = sorted(d for _, d in dated)
        print("\nstructurally plausible: %d" % len(dated))
        print("  date range: %s to %s" % (dates[0].date(), dates[-1].date()))

    bad = len(undecodable) + len(future) + len(ancient)
    verdict_bad = False

    if bad:
        verdict_bad = True
        print("\nIMPLAUSIBLE: %d IDs (%.1f%%)" % (bad, 100.0 * bad / len(ids)))
        for label, group in (("undecodable/too small", [(t, None) for t in undecodable]),
                             ("decode to the future", future),
                             ("decode to before 2006", ancient)):
            if group:
                print("  %s: %d, e.g. %s" % (label, len(group), ", ".join(t for t, _ in group[:3])))

    # float64 holds ~15-17 significant digits, so a 19-digit ID pushed through a
    # spreadsheet comes back with its tail zeroed. Chance-level is ~1 in 10,000.
    if len(rounded) > max(2, len(ids) * 0.01):
        verdict_bad = True
        print("\nFLOAT-ROUNDED: %d IDs (%.1f%%) end in '0000'" %
              (len(rounded), 100.0 * len(rounded) / len(ids)))
        print("  e.g. %s" % ", ".join(rounded[:3]))
        print("  These decode to valid-looking dates but are NOT real post IDs.")
        print("  They will 404 on every backend.")

    if big and len(float_exact) > max(2, len(big) * 0.05):
        verdict_bad = True
        print("\nFLOAT-ROUNDTRIPPED: %d of %d long IDs (%.1f%%) are exactly "
              "representable as float64." % (len(float_exact), len(big),
                                             100.0 * len(float_exact) / len(big)))
        print("  e.g. %s" % ", ".join(float_exact[:3]))
        print("  Real IDs hit that by chance only ~0.5% of the time. These have")
        print("  been through a float somewhere (pandas read_csv, JSON, JS) and")
        print("  their last 2-3 digits are wrong. They will 404 on every backend.")

    if verdict_bad:
        print("\n  Most likely: the CSV was opened and re-saved in Excel or Sheets,")
        print("  or read with pandas without dtype=str. Both destroy 19-digit ints.")
        print("  Fix: re-export from the original source with the ID column as Text,")
        print("  or read it with pd.read_csv(path, dtype={'tweet_id': str}).")
    else:
        print("\nNo structural problems found. Failures are more likely genuine")
        print("deletions/suspensions. Note this check cannot prove an ID is real,")
        print("only that it isn't obviously mangled.")

    print("\nfirst 5: %s" % ", ".join(ids[:5]))
    return 0


def fetch_one(tweet_id, order, retries, delay):
    """Try each backend in order; retry transient failures with backoff.

    Collects an error from every backend, not just the last, otherwise the
    fallback's generic message masks the first backend's specific one.
    """
    errors = []
    for name in order:
        fn = BACKENDS[name]
        err = None
        for attempt in range(retries + 1):
            try:
                return fn(tweet_id), None
            except urllib.error.HTTPError as e:
                err = "%s HTTP %s" % (name, e.code)
                if e.code in (400, 401, 403, 404):
                    break  # permanent for this backend, move on
                time.sleep(min(30, (2 ** attempt) + random.random()))
            except LookupError as e:
                err = "%s: %s" % (name, e)
                break  # backend answered, post genuinely isn't available
            except Exception as e:
                err = "%s: %s" % (name, e)
                time.sleep(min(30, (2 ** attempt) + random.random()))
        if err:
            errors.append(err)
        time.sleep(delay)
    return None, " | ".join(errors)


def load_done(path):
    """Read an existing .jsonl output back in. Returns {id: record}.

    Used both to skip already-fetched IDs and to fold prior runs into the
    final JSON array, so a resumed job still produces one complete file.
    """
    done = {}
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if rec.get("id"):
                        done[str(rec["id"])] = rec
                except Exception:
                    pass
    return done


CSV_COLS = ["id", "url", "created_at", "author_handle", "author_name", "text", "lang",
            "replies", "reposts", "likes", "quotes", "views", "bookmarks",
            "is_reply_to", "is_quote", "media_count", "media_urls", "_backend"]


def main():
    p = argparse.ArgumentParser(description="Fetch public X posts by ID, no API key.")
    p.add_argument("ids", nargs="*", help="post IDs or x.com URLs")
    p.add_argument("--from-file", help="CSV/TSV or plain text file of IDs or URLs")
    p.add_argument("--id-column", help="CSV column holding the ID (name or 0-based index)")
    p.add_argument("--limit", type=int, default=0, help="only take the first N IDs (0 = all)")
    p.add_argument("--offset", type=int, default=0, help="skip the first N IDs, for batching")
    p.add_argument("--out", help="append results as JSONL here (line-per-post, resumable)")
    p.add_argument("--json", dest="json_out", help="write a proper JSON array here")
    p.add_argument("--csv", help="also write a flat CSV here")
    p.add_argument("--backend", choices=["auto", "fxtwitter", "syndication"], default="auto")
    p.add_argument("--delay", type=float, default=0.4, help="seconds between requests")
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--workers", type=int, default=5, help=">1 to parallelise (be polite)")
    p.add_argument("--resume", action="store_true", help="skip IDs already in --out")
    p.add_argument("--pretty", action="store_true", help="pretty-print to stdout")
    p.add_argument("--dry-run", action="store_true",
                   help="validate IDs offline and report mangled ones, no network calls")
    args = p.parse_args()

    ids, seen = [], set()
    for r in args.ids:
        tid = parse_id(r)
        if tid and tid not in seen:
            seen.add(tid)
            ids.append(tid)

    if args.from_file:
        for tid in read_ids(args.from_file, args.id_column, args.limit, args.offset):
            if tid not in seen:
                seen.add(tid)
                ids.append(tid)
        print("loaded %d IDs from %s" % (len(ids), args.from_file), file=sys.stderr)

    if not ids:
        p.error("no valid post IDs given")

    if args.dry_run:
        return dry_run(ids)

    carried = []
    if args.resume and args.out:
        done = load_done(args.out)
        before = len(ids)
        carried = [done[i] for i in ids if i in done]
        ids = [i for i in ids if i not in done]
        if before != len(ids):
            print("resuming, skipping %d already fetched" % (before - len(ids)), file=sys.stderr)

    order = ["fxtwitter", "syndication"] if args.backend == "auto" else [args.backend]

    out_f = open(args.out, "a", encoding="utf-8") if args.out else None
    rows, failures = [], []

    def work(tid):
        rec, err = fetch_one(tid, order, args.retries, args.delay)
        time.sleep(args.delay)
        return tid, rec, err

    def handle(i, tid, rec, err):
        if rec is None:
            failures.append((tid, err))
            print("[%d/%d] %s FAILED (%s)" % (i, len(ids), tid, err), file=sys.stderr)
            return
        rows.append(rec)
        if out_f:
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out_f.flush()
        if args.pretty or not (args.out or args.csv or args.json_out):
            print(json.dumps(rec, ensure_ascii=False, indent=2 if args.pretty else None))
        elif i % 25 == 0 or i == len(ids):
            print("[%d/%d] ok=%d failed=%d" % (i, len(ids), len(rows), len(failures)),
                  file=sys.stderr)

    try:
        if args.workers > 1:
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                futures = {ex.submit(work, t): t for t in ids}
                for i, fut in enumerate(as_completed(futures), 1):
                    tid, rec, err = fut.result()
                    handle(i, tid, rec, err)
        else:
            for i, tid in enumerate(ids, 1):
                handle(i, *work(tid))
    except KeyboardInterrupt:
        print("\ninterrupted. %d posts already saved to %s"
              % (len(rows), args.out or "(nothing, you passed no --out)"), file=sys.stderr)
    finally:
        if out_f:
            out_f.close()

    all_rows = carried + rows

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(all_rows, f, ensure_ascii=False, indent=2)
        print("wrote %d posts to %s" % (len(all_rows), args.json_out), file=sys.stderr)

    if args.csv and all_rows:
        with open(args.csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLS, extrasaction="ignore")
            w.writeheader()
            for r in all_rows:
                r = dict(r)
                r["media_urls"] = " | ".join(r.get("media_urls") or [])
                w.writerow(r)

    if failures:
        with open("failed_ids.txt", "w", encoding="utf-8") as f:
            for tid, err in failures:
                f.write("%s\t%s\n" % (tid, err))

    print("\ndone: %d ok, %d failed" % (len(rows), len(failures)), file=sys.stderr)
    if failures:
        print("failed IDs written to failed_ids.txt", file=sys.stderr)
    return 1 if (ids and not rows) else 0


if __name__ == "__main__":
    sys.exit(main())