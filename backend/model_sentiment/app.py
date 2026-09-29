from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
 
model_path = "Main-Repository/backend/model_sentiment/modernbert_model"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path)
model.eval()
 
label_map = {0: "negative", 1: "neutral", 2: "positive"}
 
def predict(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
    pred_id = torch.argmax(outputs.logits, dim=-1).item()
    return label_map[pred_id]
 
# Try it on a few example tweets
examples = [
    "Vaccines are the reason my kids are sick today",
    "I trust these vaccines",
    "feeling like shit",
    "fuck you"
]
 
for text in examples:
    print(f"{text!r} -> {predict(text)}")