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

def test_share_url_with_query_string():
    result = classify_input("https://x.com/elonmusk/status/1234567890?s=46&t=abc123")
    assert result["type"] == "url"

def test_url_with_media_suffix():
    result = classify_input("https://x.com/elonmusk/status/1234567890/photo/1")
    assert result["type"] == "url"

def test_mobile_twitter_url():
    result = classify_input("https://mobile.twitter.com/elonmusk/status/1234567890")
    assert result["type"] == "url"

def test_url_with_surrounding_whitespace():
    result = classify_input("  https://x.com/elonmusk/status/1234567890  ")
    assert result == {"type": "url", "value": "https://x.com/elonmusk/status/1234567890"}

# --- Raw text ---

def test_plain_tweet_text():
    result = classify_input("this is just some tweet text, not a url")
    assert result["type"] == "text"

def test_text_containing_a_link_is_still_text():
    result = classify_input("Vaccines cause autism, see https://example.com/study")
    assert result["type"] == "text"

def test_text_with_a_full_stop_is_not_a_link():
    result = classify_input("vaccines.are.safe")
    assert result["type"] == "text"

def test_x_url_without_scheme():
    result = classify_input("x.com/elonmusk/status/1234567890")
    assert result["type"] == "url"

@pytest.mark.parametrize("link", [
    "https://fxtwitter.com/elonmusk/status/1234567890",
    "https://vxtwitter.com/elonmusk/status/1234567890",
    "https://fixupx.com/elonmusk/status/1234567890",
])
def test_mirror_urls(link):
    assert classify_input(link)["type"] == "url"

def test_uppercase_x_url():
    result = classify_input("https://X.com/elonmusk/status/1234567890")
    assert result["type"] == "url"

# --- Edge cases / errors ---

def test_text_too_long_raises():
    long_text = "a" * 5000
    with pytest.raises(InputValidationError):
        classify_input(long_text)

@pytest.mark.parametrize("text", ["", "   "])
def test_blank_input_raises(text):
    with pytest.raises(InputValidationError, match="Enter a claim"):
        classify_input(text)

# --- Links that aren't X posts ---

@pytest.mark.parametrize("link", [
    "https://x.com/elonmusk",                 # profile, no status id
    "https://twitter.com/search?q=vaccine",
    "x.com/home",
    "https://x.com",
    "https://x.com/elonmusk/status/notanid",
])
def test_x_link_that_isnt_a_post_raises(link):
    with pytest.raises(InputValidationError, match="doesn't point to a post"):
        classify_input(link)

@pytest.mark.parametrize("link", [
    "https://example.com/some/path",
    "http://facebook.com/posts/123",
    "www.reddit.com/r/vaccines",
    "youtube.com/watch?v=abc",
])
def test_non_x_link_raises(link):
    with pytest.raises(InputValidationError, match="Only links to X posts"):
        classify_input(link)
