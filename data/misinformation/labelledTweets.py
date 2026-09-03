import json
import pandas as pd
from pathlib import Path

def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return pd.DataFrame(records)

# 1. Load labels
labels_df = pd.read_csv(r"data\misinformation\Labeled\VaxMisinfoData.csv")
labels_df["id"] = labels_df["id"].astype(str)

# 2. Load all raw tweet JSONL files and combine
jsonl_dir = Path(r"data\misinformation")
tweet_dfs = [load_jsonl(p) for p in jsonl_dir.glob("*.jsonl")]
tweets_df = pd.concat(tweet_dfs, ignore_index=True)
tweets_df["id"] = tweets_df["id"].astype(str)

# # 3. Join on id
merged = labels_df.merge(tweets_df[["id", "text"]], on="id", how="inner")

print(f"Labels: {len(labels_df)} | Tweets: {len(tweets_df)} | Matched: {len(merged)}")
unmatched = len(labels_df) - len(merged)
if unmatched:
    print(f"Warning: {unmatched} labeled ids had no matching tweet text")

# 4. Save clean training file
merged = merged[["id", "text", "is_misinfo"]]
merged.to_csv("labelledTweets.csv", index=False)
print("Saved to data/misinformation/labelledTweets.csv")