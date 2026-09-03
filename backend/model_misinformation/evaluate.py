import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report, ConfusionMatrixDisplay
import matplotlib.pyplot as plt
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import config

# 1. Load same split used in training (same random_state = same val set)
df = pd.read_csv(config.DATA_CSV)
train_df, val_df = train_test_split(
    df,
    test_size=config.TEST_SIZE,
    random_state=config.RANDOM_SEED,
    stratify=df[config.LABEL_COL]
)

# 2. Load your trained model
tokenizer = AutoTokenizer.from_pretrained(config.OUTPUT_DIR)
model = AutoModelForSequenceClassification.from_pretrained(config.OUTPUT_DIR)
model.eval()

# 3. Run predictions on validation set
texts = val_df[config.TEXT_COL].astype(str).tolist()
true_labels = val_df[config.LABEL_COL].tolist()
predicted_labels = []

with torch.no_grad():
    for text in texts:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=config.MAX_LEN)
        outputs = model(**inputs)
        pred = torch.argmax(outputs.logits, dim=-1).item()
        predicted_labels.append(pred)

# 4. Print text report
print(classification_report(true_labels, predicted_labels, target_names=["Not Misinfo", "Misinfo"]))

# 5. Confusion matrix
cm = confusion_matrix(true_labels, predicted_labels)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Not Misinfo", "Misinfo"])
disp.plot(cmap="Blues")
plt.title("Misinformation Classifier — Confusion Matrix")
plt.savefig("confusion_matrix.png")
plt.show()