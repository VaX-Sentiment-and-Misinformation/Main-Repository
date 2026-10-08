import json

import httpx
from fastapi.testclient import TestClient

import misinformation
import sentiment
from main import app

client = TestClient(app)

POST_URL = "https://x.com/elonmusk/status/1234567890"

# Validation happens before the misinformation model is called, so no model is needed here.

def test_non_x_link_rejected():
    res = client.get("/analyse/misinformation", params={"q": "https://example.com/some/path"})
    assert res.status_code == 422
    assert "Only links to X posts" in res.json()["detail"]

def test_blank_query_rejected():
    res = client.get("/analyse/misinformation", params={"q": "   "})
    assert res.status_code == 422

# --- The fetcher and model are stubbed so no network is needed ---

def stub_model(monkeypatch):
    seen = []

    async def fake_predict(text):
        seen.append(text)
        return {"label": "misinformation", "scores": {"not_misinformation": 0.1, "misinformation": 0.9}}

    monkeypatch.setattr(misinformation, "predict", fake_predict)
    return seen

def test_post_url_analyses_fetched_text(monkeypatch):
    seen = stub_model(monkeypatch)
    # Post fetching is shared with the sentiment endpoint
    monkeypatch.setattr(sentiment, "fetch_post", lambda url, **kw: {"id": "1234567890", "text": "Vaccines cause autism"})

    res = client.get("/analyse/misinformation", params={"q": POST_URL})
    assert res.status_code == 200
    body = res.json()
    assert seen == ["Vaccines cause autism"]
    assert body["post"]["id"] == "1234567890"
    assert body["label"] == "misinformation"
    assert body["scores"]["misinformation"] == 0.9

def test_plain_text_skips_fetcher(monkeypatch):
    seen = stub_model(monkeypatch)

    def should_not_fetch(url, **kw):
        raise AssertionError("fetch_post called for plain text")

    monkeypatch.setattr(sentiment, "fetch_post", should_not_fetch)
    res = client.get("/analyse/misinformation", params={"q": "Vaccines cause autism"})
    assert res.status_code == 200
    assert res.json()["post"] is None
    assert seen == ["Vaccines cause autism"]

def test_model_down_returns_503(monkeypatch):
    monkeypatch.setattr(misinformation, "MISINFO_MODEL_URL", "http://127.0.0.1:9/predict")
    res = client.get("/analyse/misinformation", params={"q": "Vaccines cause autism"})
    assert res.status_code == 503

# --- Explanations: Ollama is stubbed with httpx.MockTransport ---

def stub_ollama(monkeypatch, handler):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(misinformation.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))

def test_explanation_sends_label_and_text(monkeypatch):
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"response": "  It contradicts the evidence.  "})

    stub_ollama(monkeypatch, handler)
    res = client.post("/analyse/misinformation/explanation", json={"text": "Vaccines cause autism", "label": "misinformation"})
    assert res.status_code == 200
    assert res.json() == {"explanation": "It contradicts the evidence."}
    assert '"Vaccines cause autism"' in sent[0]["prompt"]
    assert "CLASSIFICATION:\nMISINFORMATION\n" in sent[0]["prompt"]

def test_explanation_rejects_unknown_label():
    res = client.post("/analyse/misinformation/explanation", json={"text": "hi", "label": "maybe"})
    assert res.status_code == 422

def test_explanation_ollama_down_returns_503(monkeypatch):
    monkeypatch.setattr(misinformation, "OLLAMA_URL", "http://127.0.0.1:9/api/generate")
    res = client.post("/analyse/misinformation/explanation", json={"text": "Vaccines cause autism", "label": "misinformation"})
    assert res.status_code == 503
