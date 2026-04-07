import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

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
df.to_csv("cleaned.csv", index=False)

print(df["toxic"].value_counts())

X = df["comment_text"]
y = df["toxic"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# sparse vectorization - key word vectors
vectorizer = TfidfVectorizer(max_features=5000,
                             stop_words="english",
                             ngram_range=(1, 2)   # unigrams + bigrams
                             )

X_train_vec = vectorizer.fit_transform(X_train)  # learn + transform
X_test_vec = vectorizer.transform(X_test)        # only transform

# print(X_train_vec.shape)
# print(X_test_vec.shape)

# print(vectorizer.get_feature_names_out()[:200])


# Example model
model = LogisticRegression(max_iter=10000, random_state=0)
model.fit(X_train_vec, y_train)

print("Train accuracy:", model.score(X_train_vec, y_train))
print("Test accuracy:", model.score(X_test_vec, y_test))

# for testing the model
def predict_toxicity(text):
    # clean the input the SAME way as training data
    cleaned = clean_text(text)
    
    # vectorize (IMPORTANT: use transform, not fit_transform)
    vec = vectorizer.transform([cleaned])
    
    # predict
    pred = model.predict(vec)[0]
    prob = model.predict_proba(vec)[0][1]  # probability of toxic
    
    return pred, prob

sentence = "You are such an idiot"
pred, prob = predict_toxicity(sentence)

print("Sentence:", sentence)
print("Prediction:", "Toxic" if pred == 1 else "Not Toxic")
print("Confidence:", prob)
