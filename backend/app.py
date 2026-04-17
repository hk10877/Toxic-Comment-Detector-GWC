"""
Toxicity Detection API
----------------------
Wraps the ML classifier + RAG explanation pipeline behind a Flask HTTP API
that the Chrome extension can call.


Run:
    pip install flask flask-cors pandas scikit-learn groq
    python app.py


The server listens on http://127.0.0.1:5000
"""


import os
import re
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from groq import Groq

from dotenv import load_dotenv
load_dotenv()

# CONFIG
# DATA_PATH = os.environ.get("TOXIC_DATA_PATH", "data/train.csv")
# GROQ_API_KEY = os.environ.get(
#     "GROQ_API_KEY",
#     "",
# )
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "train.csv")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TOXIC_THRESHOLD = 0.3


# DATA + TRAINING
print("[boot] loading dataset...")
df = pd.read_csv(DATA_PATH)
df = df.drop(
    columns=[c for c in ["severe_toxic", "obscene", "threat", "insult", "identity_hate", "id"] if c in df.columns]
)
df = df.dropna(subset=["comment_text"])


def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-z\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


df["comment_text"] = df["comment_text"].apply(clean_text)


print("[boot] vectorizing...")
X = df["comment_text"]
y = df["toxic"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)


vectorizer = TfidfVectorizer(
    max_features=5000,
    stop_words="english",
    ngram_range=(1, 2),
)
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)


print("[boot] training classifier...")
model = LogisticRegression(
    max_iter=10000, random_state=0, class_weight="balanced", C=100
)
model.fit(X_train_vec, y_train)
train_acc = model.score(X_train_vec, y_train)
test_acc = model.score(X_test_vec, y_test)
print(f"[boot] train acc = {train_acc:.3f}  |  test acc = {test_acc:.3f}")


# Pre-compute document vectors for retrieval
print("[boot] pre-computing retrieval index...")
doc_vectors = vectorizer.transform(df["comment_text"].tolist())


# Groq client
client = Groq(api_key=GROQ_API_KEY)


# CORE FUNCTIONS
def retrieve_similar_comments(query: str, top_k: int = 5):
    cleaned = clean_text(query)
    q_vec = vectorizer.transform([cleaned])
    scores = cosine_similarity(q_vec, doc_vectors).flatten()
    top_idx = scores.argsort()[::-1][:top_k]
    return [
        {
            "comment_text": df.iloc[i]["comment_text"],
            "toxic": int(df.iloc[i]["toxic"]),
            "score": round(float(scores[i]), 4),
        }
        for i in top_idx
    ]


def call_groq(prompt: str, system: str, max_tokens: int = 400) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def explain(query: str, retrieved, confidence: float) -> str:
    examples = "\n".join(
        f'  {i+1}. "{r["comment_text"]}" → {"TOXIC" if r["toxic"] else "NOT TOXIC"} (sim={r["score"]})'
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



def analyze(comment: str, top_k: int = 5) -> dict:
    cleaned = clean_text(comment)
    vec = vectorizer.transform([cleaned])
    confidence = float(model.predict_proba(vec)[0][1])
    prediction = 1 if confidence >= TOXIC_THRESHOLD else 0


    result = {
        "comment": comment,
        "prediction": "Toxic" if prediction == 1 else "Not Toxic",
        "confidence": confidence,
        "explanation": None,
        "rewrite": None,
        "retrieved": None,
    }


    if prediction == 1:
        retrieved = retrieve_similar_comments(comment, top_k=top_k)
        result["retrieved"] = retrieved
        try:
            result["explanation"] = explain(comment, retrieved, confidence)
        except Exception as e:
            result["explanation"] = f"(LLM unavailable: {e})"
        try:
            result["rewrite"] = rewrite(comment)
        except Exception as e:
            result["rewrite"] = f"(LLM unavailable: {e})"


    return result


# FLASK APP
app = Flask(__name__)
# Allow the Chrome extension (chrome-extension://...) + localhost to call us
CORS(app, resources={r"/*": {"origins": "*"}})


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "train_accuracy": round(train_acc, 4),
            "test_accuracy": round(test_acc, 4),
            "dataset_size": len(df),
        }
    )



@app.route("/analyze", methods=["POST", "OPTIONS"])
def analyze_route():
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    comment = (data.get("comment") or "").strip()
    if not comment:
        return jsonify({"error": "Missing 'comment' field"}), 400
    top_k = int(data.get("top_k", 5))
    try:
        result = analyze(comment, top_k=top_k)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)


