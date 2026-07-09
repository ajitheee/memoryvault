# Running MemoryVault locally (off Emergent)

You need three things: **MongoDB**, the **backend** (FastAPI), and the **frontend** (React).
No Emergent account or key is required — extraction falls back to a zero-key mode.

---

## 1. MongoDB (pick one)

- **Easiest — MongoDB Atlas (free, no install):** create a free cluster at
  <https://www.mongodb.com/atlas>, add a database user, allow your IP, and copy the
  connection string (looks like `mongodb+srv://user:pass@cluster.xxxx.mongodb.net`).
- **Docker:** `docker run -d -p 27017:27017 --name mongo mongo:7` → use `mongodb://localhost:27017`.

## 2. Backend

```powershell
cd backend
pip install -r requirements-local.txt      # lean, Windows-friendly (no emergentintegrations / jq)
```

Create `backend\.env`:

```
MONGO_URL=mongodb://localhost:27017        # or your Atlas string
DB_NAME=memoryvault

# --- Extraction: choose ONE (or none) ---
# (a) No key at all — rule-based fallback. The app fully works; extraction is basic.
EXTRACTION_BACKEND=heuristic

# (b) OpenAI (or any OpenAI-compatible endpoint):
# EXTRACTION_BACKEND=openai
# EXTRACTION_API_KEY=sk-...
# EXTRACTION_MODEL=gpt-4o-mini

# (c) Fully local, free, no cloud — Ollama (https://ollama.com):
#   ollama pull llama3.1
# EXTRACTION_BACKEND=openai
# EXTRACTION_API_BASE=http://localhost:11434/v1
# EXTRACTION_API_KEY=ollama
# EXTRACTION_MODEL=llama3.1

# --- Semantic search (optional; default is offline keyword mode) ---
# EMBEDDING_BACKEND=openai
# EMBEDDING_API_KEY=sk-...
# EMBEDDING_MODEL=text-embedding-3-small
```

Run it:

```powershell
python -m uvicorn server:app --host 0.0.0.0 --port 8001
```

Check it's up: open <http://localhost:8001/api/> — you should see `{"service":"MemoryVault","status":"ok"}`.

## 3. Frontend

Create `frontend\.env`:

```
REACT_APP_BACKEND_URL=http://localhost:8001
```

Then:

```powershell
cd frontend
yarn install       # or: npm install
yarn start         # or: npm start   -> opens http://localhost:3000
```

## 4. See it work

1. Open <http://localhost:3000> → **Initialize Vault** (sign up).
2. **Ingest** → paste `I live in Chennai.` then `I moved to Toronto last year.`
3. **Facts** → the Chennai fact is now *superseded* by Toronto (temporal supersession).
4. Paste `I'm allergic to shellfish.` → it lands in **Pending** (high-stakes) until you confirm it.
5. **Context Pack** → type `plan a dinner` and see the token-budgeted context the AI would receive.
6. **Connect** → grab your MCP token to wire it into Claude Desktop / Cursor.

## 5. (Optional) The benchmark scoreboard

With the backend running:

```powershell
pip install mem0ai zep-cloud
$env:BENCH_BASE_URL="http://localhost:8001"
$env:MEM0_API_KEY="..."; $env:ZEP_API_KEY="..."
python backend/benchmark/harness.py --adapter all
```

Prints MemoryVault vs mem0 vs Zep on Recall / MRR / **Freshness** (supersession) / latency.
For a fair recall comparison, enable a real `EMBEDDING_BACKEND` above and call
`POST /api/index/rebuild` once first.

---

### Notes
- **Object-storage export bundles** are the only feature that needs Emergent; it's wrapped in
  try/except and simply no-ops locally. Plain **JSON export** (`GET /api/export`) works fine.
- For the best extraction quality without any cloud, use the Ollama option in (c).
