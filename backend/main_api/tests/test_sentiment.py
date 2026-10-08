from fastapi.testclient import TestClient

import sentiment
from main import app
from x_post_fetcher import PostUnavailable

client = TestClient(app)

POST_URL = "https://x.com/elonmusk/status/1234567890"

# Validation happens before the sentiment model is called, so no model is needed here.

def test_text_too_long_rejected():
    res = client.get("/analyse/sentiment", params={"q": "a" * 5000})
    assert res.status_code == 422
    assert res.json()["detail"] == "Text input is too long to be a tweet."

def test_non_x_link_rejected():
    res = client.get("/analyse/sentiment", params={"q": "https://example.com/some/path"})
    assert res.status_code == 422
    assert "Only links to X posts" in res.json()["detail"]

def test_blank_query_rejected():
    res = client.get("/analyse/sentiment", params={"q": "   "})
    assert res.status_code == 422

def test_empty_query_rejected():
    res = client.get("/analyse/sentiment", params={"q": ""})
    assert res.status_code == 422

# --- Post URLs: the fetcher and model are stubbed so no network is needed ---

def stub_model(monkeypatch):
    seen = []

    async def fake_predict(text):
        seen.append(text)
        return {"label": "negative", "scores": {"negative": 0.8, "neutral": 0.15, "positive": 0.05}}

    monkeypatch.setattr(sentiment, "predict", fake_predict)
    return seen

def test_post_url_analyses_fetched_text(monkeypatch):
    seen = stub_model(monkeypatch)
    monkeypatch.setattr(sentiment, "fetch_post", lambda url, **kw: {"id": "1234567890", "text": "Vaccines cause autism"})

    res = client.get("/analyse/sentiment", params={"q": POST_URL})
    assert res.status_code == 200
    body = res.json()
    assert seen == ["Vaccines cause autism"]
    assert body["query"] == POST_URL
    assert body["text"] == "Vaccines cause autism"
    assert body["post"]["id"] == "1234567890"
    assert body["label"] == "negative"

def test_unavailable_post_returns_404(monkeypatch):
    stub_model(monkeypatch)

    def unavailable(url, **kw):
        raise PostUnavailable("1234567890", ["fxtwitter: not found"])

    monkeypatch.setattr(sentiment, "fetch_post", unavailable)
    res = client.get("/analyse/sentiment", params={"q": POST_URL})
    assert res.status_code == 404

def test_post_without_text_rejected(monkeypatch):
    stub_model(monkeypatch)
    monkeypatch.setattr(sentiment, "fetch_post", lambda url, **kw: {"id": "1234567890", "text": ""})

    res = client.get("/analyse/sentiment", params={"q": POST_URL})
    assert res.status_code == 422

def test_plain_text_skips_fetcher(monkeypatch):
    seen = stub_model(monkeypatch)

    def should_not_fetch(url, **kw):
        raise AssertionError("fetch_post called for plain text")

    monkeypatch.setattr(sentiment, "fetch_post", should_not_fetch)
    res = client.get("/analyse/sentiment", params={"q": "Vaccines cause autism"})
    assert res.status_code == 200
    assert res.json()["post"] is None
    assert seen == ["Vaccines cause autism"]
