from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

# Validation happens before the sentiment model is called, so no model is needed here.

def test_post_url_rejected():
    res = client.get("/analyse/sentiment", params={"q": "https://x.com/elonmusk/status/1234567890"})
    assert res.status_code == 422

def test_text_too_long_rejected():
    res = client.get("/analyse/sentiment", params={"q": "a" * 5000})
    assert res.status_code == 422
    assert res.json()["detail"] == "Text input is too long to be a tweet."

def test_empty_query_rejected():
    res = client.get("/analyse/sentiment", params={"q": ""})
    assert res.status_code == 422
