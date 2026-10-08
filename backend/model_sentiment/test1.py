import pandas as pd
import numpy as np
import torch
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix

# 1. Load the test set
test_df = pd.read_csv("Main-Repository/data/sentiment/test.csv")
test_ds = Dataset.from_pandas(test_df[["clean_text", "label"]])

# 2. Load your trained model
model_path = "Main-Repository/backend/model_sentiment/modernbert_model"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path)
model.eval()

# 3. Tokenize
def tokenize(batch):
    return tokenizer(batch["clean_text"], truncation=True, padding=True, return_tensors="pt")

# 4. Run predictions in batches
device = "mps" if torch.backends.mps.is_available() else "cpu"
model.to(device)

all_preds = []
all_labels = test_df["label"].tolist()

batch_size = 16
texts = test_df["clean_text"].tolist()

for i in range(0, len(texts), batch_size):
    batch_texts = texts[i:i + batch_size]
    inputs = tokenizer(batch_texts, truncation=True, padding=True, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    preds = torch.argmax(outputs.logits, dim=-1).cpu().numpy()
    all_preds.extend(preds)

# 5. Metrics
label_names = ["negative", "neutral", "positive"]  # matches label_map 0,1,2 used earlier

print("Accuracy:", accuracy_score(all_labels, all_preds))
print("F1 macro:", f1_score(all_labels, all_preds, average="macro"))
print("\nClassification report:\n")
print(classification_report(all_labels, all_preds, target_names=label_names))
print("\nConfusion matrix (rows=true, cols=predicted):\n")
print(confusion_matrix(all_labels, all_preds))