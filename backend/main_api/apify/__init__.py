"""Apify tweet-scraper backend - plan B for historical vaccine post collection.

The official X full-archive endpoint used by x_historical_search.py needs a
Self-serve or Enterprise entitlement this project does not have, and costs $5.00
per 1,000 posts. The Apify apidojo/tweet-scraper Actor needs only a token, costs
$0.40 per 1,000, and can sort by engagement - which the official API cannot do at
all.

    python -m apify.fetch_monthly --dry-run

Posts come out in the same normalised dict shape as every other source in this
backend, so XPost.from_fetch accepts them unchanged.
"""

# fetch_monthly is deliberately NOT imported here. It is the `python -m` entry
# point, and importing it from the package __init__ makes Python load it twice -
# once as apify.fetch_monthly, once as __main__ - which it warns about. Import it
# directly instead:
#
#     from apify.fetch_monthly import fetch_month, months

from .client import ApifyError, run_actor
from .diseases import DISEASES, combined_query, tag
from .normalise import engagement, normalise

__all__ = [
    "ApifyError", "run_actor",
    "DISEASES", "combined_query", "tag",
    "normalise", "engagement",
]
