"""The nine diseases, as structured terms rather than finished query strings.

x_historical_search.DISEASES stores each disease as a pre-built query string, which
is fine for searching but useless for tagging a post after the fact. This module
keeps terms and brands as lists so both jobs can be driven off one definition:

    combined_query()   -> a single query matching any of the nine
    tag(text)          -> which of the nine a given post is about

Known duplication: the nine diseases now exist here and in x_historical_search.py.
Folding that module onto this definition is the obvious next step, but it means
editing working code, so it has been left alone deliberately.
"""

import re

__all__ = ["DISEASES", "VACCINE_TERMS", "QUERY_BUDGET", "X_QUERY_LIMIT",
           "APPENDED_CHARS", "QueryTooLong", "query_groups", "combined_query",
           "tag", "tag_counts"]

# X answers a search longer than this with zero results. Not an error, not a
# warning - an empty result set indistinguishable from "nothing matched". That
# silence is what makes the limit dangerous, and why query_groups() refuses to
# build a query that exceeds it rather than letting one be sent.
X_QUERY_LIMIT = 512

# Apify appends " lang:en since:YYYY-MM-DD until:YYYY-MM-DD" to whatever we send,
# which counts against the limit above.
APPENDED_CHARS = 42

# Measured against the live Actor, September 2026:
#     382 chars (424 sent) -> 20 results
#     475 chars (517 sent) ->  0 results
# 383-474 was never tested, so the budget is the longest length actually proven to
# work rather than the largest that theoretically fits (470). Splitting into more
# groups to respect it is free: Apify bills per tweet returned, not per run, so
# four groups of 250 cost exactly what three groups of 333 do.
#
# Do not raise this without new measurements. The failure it prevents is silent.
QUERY_BUDGET = 382

# Shared across every disease, so the combined query factors it out instead of
# repeating this list nine times.
VACCINE_TERMS = [
    "vaccine", "vaccines", "vaccinated", "vaccination", "vax", "vaxxed",
    "jab", "jabbed", "immunization", "immunisation", "booster", "shot",
]

# `terms` need a vaccine word alongside them to match; `brands` do not, because a
# brand name already names a vaccine on its own - nobody says "gardasil" about
# anything else.
#
# Ambiguous initialisms (BCG, TB, IPV, OPV) are deliberately kept in `terms` and
# never promoted to `brands`: BCG is also a consulting firm, IPV is also
# "interpersonal violence", TB is also a terabyte. The mandatory vaccine word is
# what disambiguates them.
DISEASES: dict[str, dict] = {
    "covid19": {
        "label": "COVID-19",
        "terms": ["covid", "covid19", "covid 19", "coronavirus", "sars-cov-2"],
        "brands": ["pfizer", "biontech", "moderna", "astrazeneca",
                   "comirnaty", "spikevax", "novavax", "janssen"],
    },
    "meningitis": {
        "label": "Meningitis",
        "terms": ["meningitis", "meningococcal", "menacwy", "menb"],
        "brands": ["bexsero", "trumenba", "menactra", "menveo", "nimenrix"],
    },
    "hpv": {
        "label": "HPV",
        "terms": ["hpv", "papillomavirus", "papilloma virus"],
        "brands": ["gardasil", "cervarix", "cervical cancer vaccine"],
    },
    "chickenpox": {
        "label": "Chickenpox",
        # Shingles (zostavax, shingrix) is the same virus but a different vaccine,
        # so it stays out rather than being quietly folded in here.
        "terms": ["chickenpox", "chicken pox", "varicella"],
        "brands": ["varivax", "proquad"],
    },
    "hepatitis_a": {
        "label": "Hepatitis A",
        # twinrix is the A+B combination and is omitted from both hepatitis
        # entries - including it would put the same posts in two corpora that are
        # meant to be separable.
        "terms": ["hepatitis a", "hep a", "hepa"],
        "brands": ["havrix", "vaqta", "avaxim"],
    },
    "hepatitis_b": {
        "label": "Hepatitis B",
        "terms": ["hepatitis b", "hep b", "hepb"],
        "brands": ["engerix", "recombivax", "heplisav"],
    },
    "mmr": {
        "label": "MMR",
        # proquad is MMRV, so it appears here and under chickenpox. A post can
        # legitimately carry both tags; that is correct, not a bug.
        "terms": ["mmr", "measles", "mumps", "rubella"],
        "brands": ["priorix", "proquad", "mmrv"],
    },
    "tuberculosis": {
        "label": "Tuberculosis",
        "terms": ["tuberculosis", "tb", "bcg"],
        "brands": ["bcg vaccine"],
    },
    "polio": {
        "label": "Polio",
        "terms": ["polio", "poliomyelitis", "ipv", "opv"],
        "brands": ["polio drops", "ipol"],
    },
}


class QueryTooLong(ValueError):
    """A built query would exceed what X will answer."""


def _or_group(words) -> str:
    """OR a list of search words, quoting the multi-word ones as phrases."""
    return " OR ".join('"%s"' % w if " " in w else w for w in words)


def _query_for(slugs) -> str:
    """The standard query shape for a set of diseases.

    Disease terms need a vaccine word alongside them; brands stand alone.
    Language is NOT expressed here - the Actor has a `tweetLanguage` field, and
    every character spent here comes out of the 512-char budget.
    """
    terms, brands = [], []
    for slug in slugs:
        terms.extend(DISEASES[slug]["terms"])
        brands.extend(DISEASES[slug]["brands"])
    # dict.fromkeys rather than set(): stable order, so the query string is
    # reproducible run to run - it gets recorded in run metadata.
    terms = list(dict.fromkeys(terms))
    brands = list(dict.fromkeys(brands))
    return "((%s) (%s)) OR (%s) -is:retweet" % (
        _or_group(terms), _or_group(VACCINE_TERMS), _or_group(brands))


def query_groups(budget: int = QUERY_BUDGET) -> list[tuple[list[str], str]]:
    """The nine diseases split into as few queries as fit the length budget.

    All nine in one query comes to 886 characters, which X answers with zero
    results rather than an error - the failure this function exists to avoid.
    Greedily packs diseases into a group until adding the next would overflow,
    giving three groups at the default budget.

    The cost of splitting is that VACCINE_TERMS (133 chars) repeats in every
    group. That is why the groups are packed rather than one-disease-per-query.

    Returns [(slugs, query), ...]; run each as its OWN Actor run. The Actor walks
    `searchTerms` sequentially against a single run-wide maxItems, so passing all
    three in one run lets COVID exhaust the budget before the others are reached.
    """
    groups, current = [], []
    for slug in DISEASES:
        trial = current + [slug]
        if current and len(_query_for(trial)) > budget:
            groups.append(current)
            current = [slug]
        else:
            current = trial
    if current:
        groups.append(current)

    built = [(g, _query_for(g)) for g in groups]

    # A single disease whose own query exceeds the budget cannot be split further,
    # so greedy packing would emit it over-length and X would answer with silence.
    # Fail loudly here instead: this is the one check that makes adding a tenth
    # disease, or more brand names, impossible to ship broken.
    for slugs, query in built:
        sent = len(query) + APPENDED_CHARS
        if sent > X_QUERY_LIMIT:
            raise QueryTooLong(
                "Query for %s is %d chars, %d once Apify appends its own "
                "operators - over X's %d-char limit, which X answers with zero "
                "results rather than an error. Shorten the terms for these "
                "diseases, or split them across entries in DISEASES."
                % (", ".join(slugs), len(query), sent, X_QUERY_LIMIT))
    return built


def combined_query() -> str:
    """All nine diseases in one query.

    Kept for reference and for run metadata only - DO NOT send this to the Actor.
    At 886 characters it exceeds X's 512-char search limit and returns nothing at
    all. Use query_groups() instead.
    """
    return _query_for(list(DISEASES))


def _pattern(words) -> re.Pattern:
    """Case-insensitive alternation of `words`, each on word boundaries.

    Boundaries matter more than they look: without them "tb" matches inside
    "subtle" and "hepa" inside "heparin".
    """
    return re.compile(
        r"\b(?:%s)\b" % "|".join(re.escape(w) for w in words), re.IGNORECASE)


_TERM_RE = {slug: _pattern(spec["terms"]) for slug, spec in DISEASES.items()}
_BRAND_RE = {slug: _pattern(spec["brands"]) for slug, spec in DISEASES.items()}
_VACCINE_RE = _pattern(VACCINE_TERMS)


def tag(text: str | None) -> list[str]:
    """Which of the nine diseases a post is about, as sorted slugs.

    Mirrors the query's own logic so tags agree with what was searched for: a
    disease term counts only alongside a vaccine word, a brand name counts on its
    own. Several tags are normal - an MMR post that also mentions COVID gets both.

    Best-effort keyword matching, not a classifier. It will miss a post that
    discusses a vaccine without naming it.
    """
    if not text:
        return []

    has_vaccine_word = bool(_VACCINE_RE.search(text))
    hits = [slug for slug in DISEASES
            if _BRAND_RE[slug].search(text)
            or (has_vaccine_word and _TERM_RE[slug].search(text))]
    return sorted(hits)


def tag_counts(posts) -> dict[str, int]:
    """How many of `posts` carry each disease tag, for run metadata.

    Counts overlap: the values sum to more than len(posts) when posts mention
    more than one disease.
    """
    counts = {slug: 0 for slug in DISEASES}
    for post in posts:
        for slug in post.get("diseases") or []:
            counts[slug] = counts.get(slug, 0) + 1
    return counts
