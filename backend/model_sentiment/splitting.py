import pandas as pd
from sklearn.model_selection import train_test_split
 
df = pd.read_csv("Main-Repository/data/sentiment/combined_sentiment.csv")
 
 
train_df, test_df = train_test_split(
    df, test_size=0.3, random_state=42, stratify=df["label"]
)
 
train_df.to_csv("/Users/jacquelinesurya/Monash/Final Year Project/Main-Repository/data/sentiment/train2.csv", index=False)
test_df.to_csv("/Users/jacquelinesurya/Monash/Final Year Project/Main-Repository/data/sentiment/test2.csv", index=False)
 
print("Train size:", len(train_df))
print("Test size:", len(test_df))