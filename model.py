import pandas as pd
import re
import os
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from groq import Groq

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
# load dataset
df = pd.read_csv("data/train.csv")


# cleaning steps and extracting columns we need
df = df.drop(columns=['severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate', "id"])
df = df.dropna(subset=['comment_text'])


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


# Example model
model = LogisticRegression(max_iter=10000, random_state=0, class_weight = 'balanced', C=100)
model.fit(X_train_vec, y_train)


print("Train accuracy:", model.score(X_train_vec, y_train))
print("Test accuracy:", model.score(X_test_vec, y_test))


doc_vectors = vectorizer.transform(df["comment_text"].tolist())
 
# RETRIEVAL
 
def retrieve_similar_comments(query: str, top_k: int = 5) -> list[dict]:
    cleaned = clean_text(query)
    q_vec   = vectorizer.transform([cleaned])
    scores  = cosine_similarity(q_vec, doc_vectors).flatten()
    top_idx = scores.argsort()[::-1][:top_k]
 
    return [
        {
            "comment_text": df.iloc[i]["comment_text"],
            "toxic":        int(df.iloc[i]["toxic"]),
            "score":        round(float(scores[i]), 4),
        }
        for i in top_idx
    ]
 
# GROQ CLIENT
 
# client = Groq(api_key="")  # or set env var GROQ_API_KEY
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
 
def call_groq(prompt: str, system: str, max_tokens: int = 400) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system",  "content": system},
            {"role": "user",    "content": prompt},
        ],
        temperature=0.2,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()
 
# EXPLAIN (RAG)
 
def explain(query: str, retrieved: list[dict], confidence: float) -> str:
    examples = "\n".join(
        f"  {i+1}. \"{r['comment_text']}\" → {'TOXIC' if r['toxic'] else 'NOT TOXIC'} (sim={r['score']})"
        for i, r in enumerate(retrieved)
    )
 
    prompt = f"""The following comment was flagged as TOXIC with {confidence:.0%} confidence by an ML classifier.
 
Retrieved similar comments from the moderation database:
{examples}
 
Comment to explain: "{query}"
 
Give exactly 2 sentences explaining WHY this comment is toxic.
Reference patterns from the examples above. Be specific, not generic."""
 
    system = "You are a content moderation explainer. Be concise and factual. No bullet points."
    return call_groq(prompt, system, max_tokens=150)
 
# REWRITE
 
def rewrite(query: str) -> str:
    prompt = f"""Rewrite the following toxic comment so it expresses the same underlying concern or emotion, but in a respectful, constructive way.
 
Original comment: "{query}"
 
Rules:
- Keep the same intent/meaning where possible
- Remove all insults, slurs, or personal attacks
- Sound natural, not robotic
- Return ONLY the rewritten comment, nothing else."""
 
    system = "You are a communication coach who rewrites toxic messages constructively."
    return call_groq(prompt, system, max_tokens=100)
 
# FULL PIPELINE
 
def analyze(comment: str, top_k: int = 5) -> dict:
    # Step 1 — Classify
    cleaned    = clean_text(comment)
    vec        = vectorizer.transform([cleaned])
    confidence = model.predict_proba(vec)[0][1]   # P(toxic)
    prediction = 1 if confidence >= 0.3 else 0


 
    result = {
        "comment":    comment,
        "prediction": "Toxic" if prediction == 1 else "Not Toxic",
        #"confidence": confidence,
        "explanation": None,
        "rewrite":     None,
        "retrieved":   None,
    }
 
    # Step 2 — Only explain & rewrite if toxic
    if prediction == 1:
        retrieved            = retrieve_similar_comments(comment, top_k=top_k)
        result["retrieved"]  = retrieved
        result["explanation"] = explain(comment, retrieved, confidence)
        result["rewrite"]    = rewrite(comment)
 
    return result
 
# DISPLAY
 
def display(result: dict):
    print("=" * 60)
    print(f'Comment    : "{result["comment"]}"')
    print(f'Prediction : {result["prediction"]}')
    print(f'Confidence : {result["confidence"]:.0%}')
 
    if result["prediction"] == "Toxic":
        print(f'\nExplanation:\n{result["explanation"]}')
        print(f'\nRewrite:\n{result["rewrite"]}')
    print()
 
# RUN
 
if __name__ == "__main__":
    test_comments = [
        "You are the dumbest person ever",
        "I disagree with your opinion on this topic",
        "Go back to where you came from, nobody wants you here",
    ]
 
    for comment in test_comments:
        result = analyze(comment)
        display(result)



