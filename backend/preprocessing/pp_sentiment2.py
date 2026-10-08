import pandas as pd
import re

# This dataset has no header row: tweet_id, entity, sentiment, text
df = pd.read_csv(
    "Main-Repository/data/sentiment/twitter_training_sentiment.csv",
    names=["tweet_id", "entity", "sentiment", "text"],
    header=None,
)

print(df.columns.tolist())
print(df.head())
print("Raw label distribution:\n", df["sentiment"].value_counts())

# Drop rows with missing text, and drop the off-topic "Irrelevant" class
# (your model is 3-class: negative/neutral/positive)
df = df.dropna(subset=["text", "sentiment"])
df = df[df["sentiment"] != "Irrelevant"]

# Map to the SAME scheme your training script uses: 0=negative, 1=neutral, 2=positive
label_map = {"Negative": 0, "Neutral": 1, "Positive": 2}
df["label"] = df["sentiment"].map(label_map)
df = df.dropna(subset=["label"])
df["label"] = df["label"].astype(int)

# Optional: drop exact duplicate text (note: this dataset intentionally includes
# near-duplicate paraphrases per tweet_id as a form of augmentation -- exact
# dupes only are removed here, paraphrases are kept)
df = df.drop_duplicates(subset=["text"])


def clean_text(text):
    text = str(text)
    text = re.sub(r"http\S+", "", text)                       # remove links
    text = re.sub(r"<user>", "", text, flags=re.IGNORECASE)   # remove placeholder
    text = re.sub(r"@\w+", "", text)                          # remove @mentions
    text = re.sub(r"#(\w+)", r"\1", text)                     # #vaccine -> vaccine
    text = text.replace('"', "").strip()
    text = re.sub(r"\s+", " ", text)                          # collapse extra spaces
    return text                                                # <-- fixed: was unindented


def remove_emoji(text):
    emoji_pattern = re.compile(
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
    return emoji_pattern.sub("", text)                         # <-- fixed: was unindented


df["clean_text"] = df["text"].apply(clean_text)
df["clean_text"] = df["clean_text"].apply(remove_emoji)

df = df[df["clean_text"].str.len() > 0]

df[["tweet_id", "clean_text", "label"]].to_csv(
    "cleaned_entity_sentiment.csv", index=False
)

print(df.head())
print("Cleaned label distribution:\n", df["label"].value_counts(normalize=True))
print("Saved", len(df), "rows to cleaned_entity_sentiment.csv")

import pandas as pd

# 1. Load both cleaned datasets
vaccine_df = pd.read_csv("Main-Repository/data/sentiment/cleaned_tweets_sentiment.csv")     # label: -1.0 / 0.0 / 1.0
entity_df = pd.read_csv("Main-Repository/data/sentiment/cleaned_entity_sentiment.csv")      # label: 0 / 1 / 2

print("Vaccine label distribution (raw):\n", vaccine_df["label"].value_counts())
print("\nEntity label distribution (raw):\n", entity_df["label"].value_counts())

# 2. Align label encodings -- both need to end up as 0=negative, 1=neutral, 2=positive
vaccine_label_map = {-1.0: 0, 0.0: 1, 1.0: 2}
vaccine_df["label"] = vaccine_df["label"].map(vaccine_label_map)

# entity_df is already 0/1/2 from the previous preprocessing step -- no change needed

# 3. Keep only the common columns so the schemas match
vaccine_df = vaccine_df[["tweet_id", "clean_text", "label"]].copy()
entity_df = entity_df[["tweet_id", "clean_text", "label"]].copy()

# Tag source in case you want to inspect/weight by domain later
vaccine_df["source"] = "vaccine"
entity_df["source"] = "entity"

# 4. Combine
combined = pd.concat([vaccine_df, entity_df], ignore_index=True)

# 5. Drop rows where mapping failed (shouldn't happen, but safety check)
combined = combined.dropna(subset=["label", "clean_text"])
combined["label"] = combined["label"].astype(int)

# 6. Drop duplicate text across the combined set (in case the same tweet appears in both)
before = len(combined)
combined = combined.drop_duplicates(subset=["clean_text"])
print(f"\nDropped {before - len(combined)} duplicate rows across combined set")

# 7. Shuffle so train/test splits later aren't domain-ordered
combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)

print("\nCombined label distribution:\n", combined["label"].value_counts(normalize=True))
print("\nCombined source distribution:\n", combined["source"].value_counts())

combined.to_csv("combined_sentiment.csv", index=False)
print(f"\nSaved {len(combined)} rows to combined_sentiment.csv")