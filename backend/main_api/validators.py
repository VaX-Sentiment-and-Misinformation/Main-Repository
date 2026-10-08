import re

# Share links usually carry a query string (?s=20&t=...) and can point at a
# photo or video inside the post (/photo/1), so allow both after the ID.
# The scheme is optional so a pasted "x.com/user/status/123" still works, and
# embed-fixer mirrors (fxtwitter, vxtwitter, fixupx) resolve to the same post.
X_DOMAINS = r"(www\.|mobile\.)?(twitter|x|fxtwitter|vxtwitter|fixupx|fixvx)\.com"
TWEET_URL_PATTERN = re.compile(
    r"^(https?://)?" + X_DOMAINS + r"/\w+/status/\d+(/[\w/]*)?(\?\S*)?$",
    re.IGNORECASE,
)

# An X/Twitter link that isn't a post, e.g. a profile or search page
X_DOMAIN_PATTERN = re.compile(r"^(https?://)?" + X_DOMAINS + r"(/|\?|$)", re.IGNORECASE)

# Input that is a link and nothing else. Text that merely contains a link
# (a claim followed by its source) is still treated as text.
LINK_PATTERN = re.compile(r"^(https?://|www\.)\S+$|^[\w-]+(\.[\w-]+)*\.[a-z]{2,}/\S*$", re.IGNORECASE)

MAX_TEXT_LENGTH = 4000  # generous cap for raw tweet text

class InputValidationError(Exception):
    pass

def classify_input(text: str) -> dict:
    """Classify input as a tweet URL or raw tweet text, and validate it."""
    text = text.strip()
    if not text:
        raise InputValidationError("Enter a claim or a link to an X post.")

    if TWEET_URL_PATTERN.match(text):
        return {"type": "url", "value": text}

    if X_DOMAIN_PATTERN.match(text):
        raise InputValidationError(
            "That X link doesn't point to a post. Open the post and copy its link, "
            "which looks like x.com/username/status/123..."
        )

    if LINK_PATTERN.match(text):
        raise InputValidationError(
            "Only links to X posts are supported. Paste an X post link, or paste the claim itself as text."
        )

    if len(text) > MAX_TEXT_LENGTH:
        raise InputValidationError("Text input is too long to be a tweet.")

    return {"type": "text", "value": text}
