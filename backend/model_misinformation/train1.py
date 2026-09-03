import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from transformers import (
    BertTokenizerFast, BertForSequenceClassification,
    TrainingArguments, Trainer
)
from dataset import MisinfoDataset
import config

# 1. Load merged labeled data
df = pd.read_csv(config.DATA_CSV)
print(f"Total rows: {len(df)}")
print(df[config.LABEL_COL].value_counts())

# 2. Split into train/val
train_df, val_df = train_test_split(
    df,
    test_size=config.TEST_SIZE,
    random_state=config.RANDOM_SEED,
    stratify=df[config.LABEL_COL]  # keeps class balance consistent across split
)
print(f"Train: {len(train_df)} | Val: {len(val_df)}")

# 3. Tokenizer + model
tokenizer = BertTokenizerFast.from_pretrained(config.MODEL_NAME)
model = BertForSequenceClassification.from_pretrained(
    config.MODEL_NAME, num_labels=config.NUM_LABELS
)

# 4. Build datasets
train_ds = MisinfoDataset(train_df, tokenizer, config.MAX_LEN, config.TEXT_COL, config.LABEL_COL)
val_ds = MisinfoDataset(val_df, tokenizer, config.MAX_LEN, config.TEXT_COL, config.LABEL_COL)

# 5. Metrics
def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1": f1_score(labels, preds),
        "precision": precision_score(labels, preds),
        "recall": recall_score(labels, preds),
    }

# 6. Training args
training_args = TrainingArguments(
    output_dir=config.OUTPUT_DIR,
    num_train_epochs=config.EPOCHS,
    per_device_train_batch_size=config.BATCH_SIZE,
    per_device_eval_batch_size=config.BATCH_SIZE,
    learning_rate=config.LEARNING_RATE,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    logging_steps=50,
)

# 7. Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    compute_metrics=compute_metrics,
)

trainer.train()

# 8. Save final model
trainer.save_model(config.OUTPUT_DIR)
tokenizer.save_pretrained(config.OUTPUT_DIR)
print(f"Model saved to {config.OUTPUT_DIR}")