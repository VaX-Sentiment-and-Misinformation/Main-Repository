"""Misinformation model microservice: serves the fine-tuned ModernBERT classifier over HTTP.

Run (from this folder):
    uvicorn app:app --port 8002

The weights are not in git. Put the saved model folder (config.json,
model.safetensors, tokenizer files) at MODEL_DIR, or point the
MISINFO_MODEL_DIR env var at it.
"""

import html
import os
import re
import unicodedata
from contextlib import asynccontextmanager
from pathlib import Path

import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_DIR = Path(os.getenv("MISINFO_MODEL_DIR", Path(__file__).parent / "savedModel" / "final_model"))
BATCH_SIZE = 32
MAX_LENGTH = 256  # same as trial.py

# The model's config.json uses NOT_MISINFORMATION / MISINFORMATION
LABEL_MAP = {0: "not_misinformation", 1: "misinformation"}

# Curly quotes, en/em dashes, ellipsis and non-breaking space -> ASCII
PUNCTUATION = str.maketrans({
    0x2019: "'", 0x2018: "'", 0x201C: '"', 0x201D: '"',
    0x2013: "-", 0x2014: "-", 0x2026: "...", 0x00A0: " ",
})


def clean_text(text: str) -> str:
    """Same cleaning as the team's trial.py, so scores match it exactly."""
    text = html.unescape(text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)        # remove links
    text = re.sub(r"(?<!\w)@\w+", " ", text)                  # remove @mentions
    text = re.sub(r"^\s*RT\s*:?", "", text, flags=re.I)       # remove retweet prefix
    text = text.translate(PUNCTUATION)
    text = unicodedata.normalize("NFKD", text)                # strip accents
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\x00-\x7f]", " ", text)                 # remove emojis / other non-ASCII
    text = re.sub(r"""[^A-Za-z0-9\s.,!?'":;()/%+\-]""", " ", text)  # keep useful punctuation
    return re.sub(r"\s+", " ", text).strip()


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
        inputs = tokenizer(
            texts[i:i + BATCH_SIZE], truncation=True, max_length=MAX_LENGTH, padding=True, return_tensors="pt"
        ).to(device)
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
