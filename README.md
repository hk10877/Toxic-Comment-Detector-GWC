Tonecheck — Toxicity Diagnostic
A Chrome extension frontend for an ML-based toxicity classifier with RAG-powered explanations and constructive rewrites.

A Chrome extension frontend for an ML-based toxicity classifier with RAG-powered explanations and constructive rewrites.

> Built as a **Girls Who Code** at **UT Austin** project.

```
Toxic-Comment-Detector-GWC/
├── backend/
│   ├── app.py              # Flask API wrapping the classifier
│   └── requirements.txt
├── data/
│   └── train.csv           # Jigsaw toxicity dataset
├── extension/
│   ├── manifest.json
│   ├── popup.html          # Main UI
│   ├── popup.css           # Editorial terminal-noir styling
│   ├── popup.js            # Wires UI to backend
│   ├── background.js       # Right-click "check tone" context menu
│   ├── content.js          # Placeholder for future in-page features
│   └── icons/              # 16/32/48/128 px
├── .env                    # Groq API key (not checked in)
├── model.py                # Original training script
└── README.md
```

Trains a TF-IDF + Logistic Regression classifier on the Jigsaw dataset at startup (~10–30 seconds)
Exposes two HTTP endpoints on http://127.0.0.1:5000
For toxic inputs, calls Groq (llama-3.3-70b) to generate a two-sentence diagnostic and a constructive rewrite
Frontend (Chrome extension)

## How it works

**Backend (Python / Flask)**
- Trains a TF-IDF + Logistic Regression classifier on the Jigsaw dataset at startup (~10–30 seconds)
- Exposes two HTTP endpoints on `http://127.0.0.1:5000`
- For toxic inputs, calls Groq (llama-3.3-70b) to generate a two-sentence diagnostic and a constructive rewrite

**Frontend (Chrome extension)**
- Sends text to the backend, renders the verdict (Flagged / Clear) with a confidence gauge
- For flagged text, shows two tabs: **why** (explanation) and **rewrite** (constructive version)
- Right-click any text on any webpage → "Check tone with Tonecheck" → auto-analyzes

The UI
States — the results panel cycles through four states: idle (resting wave), loading (animated bar with classify · explain · rewrite steps), result, and error.

## Setup

### 1. Install Python dependencies

From the project root, in PowerShell:

```powershell
pip install -r backend/requirements.txt
pip install python-dotenv
```

### 2. Set up your Groq API key

Create a `.env` file in the project root (same level as the `backend/` and `extension/` folders) with this single line:

```
GROQ_API_KEY=gsk_your_actual_key_here
```

Get a key at [console.groq.com/keys](https://console.groq.com/keys). No quotes, no spaces around the `=`.

> **Windows file extension gotcha:** Windows hides `.txt` by default, so your file may actually be named `.env.txt`. Check with `Get-ChildItem -Force | Where-Object { $_.Name -like ".env*" }` and rename if needed.

### 3. Make sure `app.py` reads the `.env` file

Open `backend/app.py` and confirm these lines exist near the top:

```python
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found. Check your .env file at the project root.")
```

Also confirm the dataset path is correct for the repo structure:

```python
DATA_PATH = os.environ.get("TOXIC_DATA_PATH", "../data/train.csv")
```

### 4. Load the Chrome extension (one-time)

1. Open Chrome → `chrome://extensions`
2. Toggle **Developer mode** on (top right)
3. Click **Load unpacked**
4. Select the `extension/` folder
5. Click the puzzle-piece icon in Chrome's toolbar → pin Tonecheck so it stays visible

Customizing
Change	Where
Toxic threshold	TOXIC_THRESHOLD = 0.3 in backend/app.py
Accent color	--signal in extension/popup.css (currently electric lime #c7ff3d)
API base URL	API_BASE in extension/popup.js if you move the server off localhost
LLM model	call_groq() in backend/app.py (currently llama-3.3-70b-versatile)
Number of retrieved matches	top_k in the JSON sent from popup.js (default 5)
Tech stack
Classifier: TF-IDF (unigrams + bigrams, 5000 features) + Logistic Regression (class_weight="balanced", C=100)
Retrieval: Cosine similarity over TF-IDF vectors (used internally for RAG context; not exposed in UI)
Explanation / rewrite: Groq API with llama-3.3-70b-versatile
Server: Flask + flask-cors
Extension: Manifest V3, vanilla JS/CSS, Fraunces (serif) + JetBrains Mono (mono)
Security
The Groq API key lives in .env and is loaded via python-dotenv. Never commit .env — add it to .gitignore if you haven't. Rotate the key immediately if it's ever exposed in a shared file, chat, or repo.

## Running it

Every time you want to use the extension:

### Start the backend

In PowerShell, from the project root:

```powershell
cd backend
python app.py
```

Wait until you see:

```
[boot] train acc = 0.98  |  test acc = 0.94
 * Running on http://127.0.0.1:5000
```

**Leave this terminal open.** Minimize it — don't close it. Press `Ctrl+C` when you're done.

### Verify the server is up

Open a second PowerShell window and run:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/health
```

Or just paste `http://127.0.0.1:5000/health` into your browser's address bar. You should see JSON with `"status":"ok"`.

### Use the extension

1. Click the Tonecheck icon in Chrome
2. Check the top right — a lime dot pulsing "online" means the backend is reachable
3. Type something into the specimen box
4. Click **Run analysis** (or hit `Ctrl+Enter`)

**Right-click flow:** Select any text on any webpage → right-click → **Check tone with Tonecheck**. The popup opens pre-filled and auto-runs.

---

## The UI

**States** — the results panel cycles through four states: `idle` (resting wave), `loading` (animated bar with classify · explain · rewrite steps), `result`, and `error`.

**Verdict strip** — Large serif tag ("Flagged" in coral for toxic, "Clear" in green for safe) paired with an animated confidence gauge showing percent confidence.

**Tabs** — Only appear when flagged. Two tabs: **why** (two-sentence diagnostic from llama-3.3) and **rewrite** (constructive rewording with a copy button). Safe results get a compact "no markers detected" confirmation instead.

**Drafts persist** across popup closes via `chrome.storage.local`, so if you accidentally close the popup mid-typing, your text comes back when you reopen.

---

## Customizing

| Change | Where |
|---|---|
| Toxic threshold | `TOXIC_THRESHOLD = 0.3` in `backend/app.py` |
| Accent color | `--signal` in `extension/popup.css` (currently electric lime `#c7ff3d`) |
| API base URL | `API_BASE` in `extension/popup.js` if you move the server off localhost |
| LLM model | `call_groq()` in `backend/app.py` (currently `llama-3.3-70b-versatile`) |
| Number of retrieved matches | `top_k` in the JSON sent from `popup.js` (default 5) |

---

## Tech stack

- **Classifier:** TF-IDF (unigrams + bigrams, 5000 features) + Logistic Regression (`class_weight="balanced"`, C=100)
- **Retrieval:** Cosine similarity over TF-IDF vectors (used internally for RAG context; not exposed in UI)
- **Explanation / rewrite:** Groq API with `llama-3.3-70b-versatile`
- **Server:** Flask + flask-cors
- **Extension:** Manifest V3, vanilla JS/CSS, Fraunces (serif) + JetBrains Mono (mono)

---

## Security

The Groq API key lives in `.env` and is loaded via `python-dotenv`. **Never commit `.env`** — add it to `.gitignore` if you haven't. Rotate the key immediately if it's ever exposed in a shared file, chat, or repo.

For local development only. If you want to deploy the backend somewhere hosted, at minimum add rate limiting (`flask-limiter`) and put authentication in front of the `/analyze` endpoint.

---

## Credits

This project was built as part of **Girls Who Code** at **UT Austin**, a program dedicated to closing the gender gap in technology and building the largest pipeline of future female and non-binary engineers.

### Team

- **Harshita Kumari** — Project Manager, AI/ML Engineer
- **Benita Benjamin** — AI/ML Engineer
- **Harschitha Sundar** — AI/ML Engineer
- **Kaycee Gomez** — AI/ML Engineer
