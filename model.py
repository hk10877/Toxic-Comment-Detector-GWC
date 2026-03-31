import pandas as pd
import re

# load dataset
df = pd.read_csv("data/train.csv")

# cleaning steps and extracting columns we need
df = df.drop(columns=['severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate', "id"])
df = df.dropna(subset=['comment_text'])

# df = df['comment_text'].str.strip()

# cleaning the text
def clean_text(text):
    text = text.lower()   
    text = re.sub(r"http\S+", "", text)  # remove links
    text = re.sub(r"[^a-z\s]", "", text)  # remove punctuation/numbers
    text = re.sub(r"\s+", " ", text).strip()  # remove
    return text

df['comment_text'] = df['comment_text'].apply(clean_text)

# View the cleaned dataset
df = df.to_csv("cleaned.csv", index=False)



