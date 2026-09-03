import pandas as pd
import re
 
df = pd.read_csv("Main-Repository/data/sentiment/sentimentvaccine1.csv")
print(df.columns.tolist())
print(df.head())
df = df.dropna(subset=["safe_text", "label"])
df = df.drop_duplicates(subset=["safe_text"])

def clean_text(text):
    text = str(text)
    text = re.sub(r"http\S+", "", text)      # remove links
    text = re.sub(r"<user>", "", text, flags=re.IGNORECASE)  # remove placeholder
    text = re.sub(r"@\w+", "", text)          # remove @mentions
    text = re.sub(r"#(\w+)", r"\1", text)     # #vaccine -> vaccine
    text = text.replace('"', "").strip()
    text = re.sub(r"\s+", " ", text)          # collapse extra spaces
    return text

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
    return emoji_pattern.sub("", text)
 
df["clean_text"] = df["safe_text"].apply(clean_text)
df["clean_text"] = df["clean_text"].apply(remove_emoji)

 
df = df[df["clean_text"].str.len() > 0]
 
df = df[df["label"].isin([-1.0, 0.0, 1.0])]
 
df[["tweet_id", "clean_text", "label", "agreement"]].to_csv("cleaned_tweets_sentiment.csv", index=False)
 
print(df.head())
print("Saved", len(df), "rows to cleaned_tweets.csv")