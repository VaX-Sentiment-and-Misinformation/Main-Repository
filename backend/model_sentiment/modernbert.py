import torch
from sklearn.utils.class_weight import compute_class_weight

import numpy as np
import pandas as pd
import torch.nn as nn
from datasets import Dataset
from sklearn.metrics import accuracy_score, f1_score, classification_report
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
)

# ---- Config ----
MODEL_NAME = "answerdotai/ModernBERT-base"   # or PREV_MODEL_DIR if continuing training
NUM_LABELS = 3
OUTPUT_DIR = "Main-Repository/backend/model_sentiment/modernbert_model_weighted2"

# 1. Load data
train_df = pd.read_csv("Main-Repository/data/sentiment/train2.csv")
test_df = pd.read_csv("Main-Repository/data/sentiment/test2.csv")

train_ds = Dataset.from_pandas(train_df[["clean_text", "label"]]).rename_column("label", "labels")
test_ds = Dataset.from_pandas(test_df[["clean_text", "label"]]).rename_column("label", "labels")

# 2. Model + tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=NUM_LABELS)

def tokenize(batch):
    return tokenizer(batch["clean_text"], truncation=True)

train_ds = train_ds.map(tokenize, batched=True).remove_columns(["clean_text"])
test_ds = test_ds.map(tokenize, batched=True).remove_columns(["clean_text"])

collator = DataCollatorWithPadding(tokenizer=tokenizer)

# 3. Your computed class weights: negative=3.1360, neutral=0.6862, positive=0.8171

class_weights = compute_class_weight(
    class_weight="balanced",
    classes=np.unique(train_df["label"]),
    y=train_df["label"],
)
class_weights = torch.tensor(class_weights, dtype=torch.float)

class WeightedTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits
        loss_fct = nn.CrossEntropyLoss(weight=class_weights.to(logits.device))
        loss = loss_fct(logits, labels)
        return (loss, outputs) if return_outputs else loss

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1_macro": f1_score(labels, preds, average="macro"),
        "f1_weighted": f1_score(labels, preds, average="weighted"),
    }

# 4. Training args -- SAME as your original baseline run, only the trainer class changes
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=3,
    eval_strategy="epoch",
    save_strategy="epoch",
    logging_steps=50,
    load_best_model_at_end=True,
    metric_for_best_model="f1_macro",
)

# The only real change vs. your original script: WeightedTrainer instead of Trainer
trainer = WeightedTrainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=test_ds,
    data_collator=collator,
    compute_metrics=compute_metrics,
)

trainer.train()
metrics = trainer.evaluate()
print(metrics)

# Per-class breakdown -- this is what tells you if negative F1 actually improved
preds = trainer.predict(test_ds)
y_pred = np.argmax(preds.predictions, axis=-1)
y_true = test_ds["labels"]
print(classification_report(y_true, y_pred, target_names=["negative", "neutral", "positive"], digits=3))

trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"Model saved to {OUTPUT_DIR}")