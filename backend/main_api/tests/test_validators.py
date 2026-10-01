import pytest
from validators import classify_input, InputValidationError

# --- URL detection ---

def test_valid_twitter_url():
    result = classify_input("https://twitter.com/elonmusk/status/1234567890")
    assert result == {"type": "url", "value": "https://twitter.com/elonmusk/status/1234567890"}

def test_valid_x_url():
    result = classify_input("https://x.com/elonmusk/status/1234567890")
    assert result["type"] == "url"

def test_url_without_https():
    result = classify_input("http://x.com/elonmusk/status/1234567890")
    assert result["type"] == "url"

def test_url_with_trailing_slash():
    result = classify_input("https://x.com/elonmusk/status/1234567890/")
    assert result["type"] == "url"

# --- Raw text ---

def test_plain_tweet_text():
    result = classify_input("this is just some tweet text, not a url")
    assert result["type"] == "text"

def test_text_that_looks_like_a_url_but_isnt_twitter():
    result = classify_input("https://example.com/some/path")
    assert result["type"] == "text"  # doesn't match twitter/x pattern, treated as text

# --- Edge cases / errors ---

def test_text_too_long_raises():
    long_text = "a" * 5000
    with pytest.raises(InputValidationError):
        classify_input(long_text)

def test_malformed_twitter_url_falls_back_to_text():
    # missing status id -> doesn't match URL pattern, so treated as raw text
    result = classify_input("https://x.com/elonmusk")
    assert result["type"] == "text"