# Tonecheck — Toxicity Diagnostic

A Chrome extension frontend for your ML-based toxicity classifier + RAG explanation pipeline.

```
toxicity-extension/
├── backend/
│   ├── app.py              # Flask API wrapping your classifier
│   └── requirements.txt
└── extension/
    ├── manifest.json
    ├── popup.html          # Main UI
    ├── popup.css           # Editorial terminal-noir styling
    ├── popup.js            # Wires UI to backend
    ├── background.js       # Right-click "check tone" context menu
    ├── content.js          # Placeholder for future in-page features
    └── icons/              # 16/32/48/128 px
```

---

## 1. Backend setup

The Flask server wraps your exact training + analysis code and exposes two endpoints:

| Method | Path        | Purpose                                                      |
|--------|-------------|--------------------------------------------------------------|
| GET    | `/health`   | Returns server status + train/test accuracy                  |
| POST   | `/analyze`  | `{"comment": "..."}` → prediction, confidence, explanation, rewrite, similar matches |

### Install & run

```bash
cd backend
pip install -r requirements.txt

# Place your Jigsaw train.csv in backend/data/train.csv
# (or set TOXIC_DATA_PATH env var to point elsewhere)
mkdir -p data
cp /path/to/your/train.csv data/train.csv

python app.py
```

The server trains once at boot (takes 10–30 seconds depending on dataset size) and then listens on **http://127.0.0.1:5000**.

> **Security note:** the Groq API key is hardcoded as a fallback in `app.py`. Before deploying anywhere non-local, move it to an environment variable:
> ```bash
> export GROQ_API_KEY="gsk_..."
> ```
> and remove the hardcoded fallback.

### Verify it works

```bash
curl http://127.0.0.1:5000/health
curl -X POST http://127.0.0.1:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"comment":"You are the dumbest person ever"}'
```

---

## 2. Load the Chrome extension

1. Open Chrome → `chrome://extensions`
2. Toggle **Developer mode** on (top right)
3. Click **Load unpacked**
4. Select the `extension/` folder
5. Pin the Tonecheck icon to your toolbar

That's it. Click the icon, paste text, hit **Run analysis**.

---

## 3. Using it

### Main popup
- Type or paste text into the specimen box
- Click **Run analysis** or hit `Ctrl/Cmd+Enter`
- If **Clear** verdict → done
- If **Flagged** verdict → switch between three tabs:
  - **Why** — two-sentence diagnostic from llama-3.3
  - **Rewrite** — constructive rewording (with copy button)
  - **Matches** — nearest similar comments from the training corpus

### Right-click context menu
Select any text on any webpage → right-click → **Check tone with Tonecheck**. The popup opens pre-filled and auto-runs.

### Status indicator
The top-right dot shows backend connectivity:
- Lime pulse = online (with test accuracy shown)
- Red = offline — start `python app.py`
- Click **recheck server** in the footer to re-ping

---

## 4. How the UI works

- **State-driven rendering.** Four states — `idle`, `loading`, `result`, `error` — swap inside one results panel.
- **Verdict strip.** Large serif tag ("Flagged"/"Clear") + animated confidence gauge.
- **Tabs only appear when toxic.** Safe results get a compact confirmation instead.
- **Drafts persist** across popup closes via `chrome.storage.local`.

---

## 5. Customizing

- **Toxic threshold:** change `TOXIC_THRESHOLD = 0.3` in `app.py`.
- **Accent color:** change `--signal` in `popup.css` (currently electric lime `#c7ff3d`).
- **API base:** change `API_BASE` in `popup.js` if you move the server off localhost.
- **Model:** `app.py` uses `llama-3.3-70b-versatile` via Groq — swap in `call_groq()`.

---

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| Status dot stays red | Backend isn't running. Run `python app.py`. |
| `CORS` errors in console | Make sure `flask-cors` is installed and you're hitting `127.0.0.1:5000`. |
| Extension popup is blank | Reload it from `chrome://extensions` after any file edit. |
| "LLM unavailable" in explanation/rewrite | Groq API key invalid, rate limited, or no internet. The classifier still works. |
| Context menu doesn't open popup | `chrome.action.openPopup` needs Chrome 127+; otherwise click the icon manually — the selected text will still be waiting. |
