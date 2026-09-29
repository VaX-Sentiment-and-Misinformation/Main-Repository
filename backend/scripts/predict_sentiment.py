"""Re-run the sentiment model over the labelled vaccine tweets.

Rewrites predicted_sentiment and confidence in misinfo_sentiment_predictions.csv
using the model in backend/model_sentiment/, with the same text cleaning the
model service uses. Run build_sentiment_trend.py afterwards to refresh the
Trends page.

Usage (from repo root, with the model weights in place):
    backend/venv/bin/python backend/scripts/predict_sentiment.py
"""

import csv
import sys
from collections import Counter
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend/model_sentiment"))
from app import LABEL_MAP, MODEL_DIR, clean_text, pick_device  # noqa: E402

PREDICTIONS = REPO / "data/misinformation/Labeled/misinfo_sentiment_predictions.csv"
BATCH_SIZE = 32


def main() -> None:
    with PREDICTIONS.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames
        rows = list(reader)

    device = pick_device()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).to(device).eval()

    texts = [clean_text(r["text"]) for r in rows]
    for i in range(0, len(texts), BATCH_SIZE):
        inputs = tokenizer(texts[i:i + BATCH_SIZE], truncation=True, max_length=256, padding=True, return_tensors="pt").to(device)
        with torch.no_grad():
            probs = model(**inputs).logits.softmax(dim=-1).cpu()
        for row, p in zip(rows[i:i + BATCH_SIZE], probs):
            pred_id = int(p.argmax())
            row["predicted_sentiment"] = LABEL_MAP[pred_id]
            row["confidence"] = float(p[pred_id])

    with PREDICTIONS.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(r["predicted_sentiment"] for r in rows)
    print(f"-> {PREDICTIONS.relative_to(REPO)}  ({len(rows)} tweets, model {MODEL_DIR.name}, {device})")
    for label in LABEL_MAP.values():
        print(f"  {label:<9} {counts[label]:>5}  {100 * counts[label] / len(rows):.1f}%")


if __name__ == "__main__":
    main()
