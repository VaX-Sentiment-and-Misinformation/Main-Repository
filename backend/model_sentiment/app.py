"""Sentiment model microservice: serves the fine-tuned ModernBERT classifier over HTTP.

Run (from this folder):
    uvicorn app:app --port 8001

The weights are not in git. Train them with modernbert.py and put the saved
final_model folder (config.json, model.safetensors, tokenizer files) at MODEL_DIR,
or point the SENTIMENT_MODEL_DIR env var at it (e.g. the older
modernbert_sentiment_v3 from train_sentiment_colab.ipynb).
"""

import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_DIR = Path(os.getenv("SENTIMENT_MODEL_DIR", Path(__file__).parent / "modernbert_model_weighted2" / "final_model"))
BATCH_SIZE = 32

# Training data encodes labels as 0/1/2 (see train_sentiment_colab.ipynb)
LABEL_MAP = {0: "negative", 1: "neutral", 2: "positive"}

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U00002600-\U000026FF"  # misc symbols
    "]+",
    flags=re.UNICODE,
)


def clean_text(text: str) -> str:
    """Same cleaning the training data goes through in train_sentiment_colab.ipynb."""
    text = re.sub(r"http\S+", "", text)                       # remove links
    text = re.sub(r"<(user|url)>", "", text, flags=re.IGNORECASE)  # remove dataset placeholders
    text = re.sub(r"@\w+", "", text)                          # remove @mentions
    text = re.sub(r"#(\w+)", r"\1", text)                     # #vaccine -> vaccine
    text = text.replace('"', "").strip()
    text = re.sub(r"\s+", " ", text)                          # collapse extra spaces
    return EMOJI_PATTERN.sub("", text)


def pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


models = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load once on startup so each request only pays for inference
    device = pick_device()
    models["tokenizer"] = AutoTokenizer.from_pretrained(MODEL_DIR)
    models["model"] = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).to(device).eval()
    models["device"] = device
    yield
    models.clear()


app = FastAPI(lifespan=lifespan)


class PredictRequest(BaseModel):
    texts: list[str]


@app.get("/")
def health_check():
    return {"status": "healthy", "model": MODEL_DIR.name, "device": models.get("device")}


@app.post("/predict")
def predict(payload: PredictRequest):
    tokenizer, model, device = models["tokenizer"], models["model"], models["device"]
    texts = [clean_text(t) for t in payload.texts]

    results = []
    for i in range(0, len(texts), BATCH_SIZE):
        inputs = tokenizer(texts[i:i + BATCH_SIZE], truncation=True, padding=True, return_tensors="pt").to(device)
        with torch.no_grad():
            probs = model(**inputs).logits.softmax(dim=-1).cpu()
        for p in probs:
            pred_id = int(p.argmax())
            results.append({
                "label": LABEL_MAP[pred_id],
                "score": round(float(p[pred_id]), 4),
                "scores": {LABEL_MAP[i]: round(float(p[i]), 4) for i in LABEL_MAP},
            })
    return {"predictions": results}
