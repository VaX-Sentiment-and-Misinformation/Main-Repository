import re

TWEET_URL_PATTERN = re.compile(
    r"^https?://(www\.)?(twitter|x)\.com/\w+/status/\d+/?$"
)

MAX_TEXT_LENGTH = 4000  # generous cap for raw tweet text

class InputValidationError(Exception):
    pass

def classify_input(text: str) -> dict:
    """Classify input as a tweet URL or raw tweet text, and validate it."""
    if TWEET_URL_PATTERN.match(text):
        return {"type": "url", "value": text}

    if len(text) > MAX_TEXT_LENGTH:
        raise InputValidationError("Text input is too long to be a tweet.")

    return {"type": "text", "value": text}