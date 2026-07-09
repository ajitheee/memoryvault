# MemoryVault

**Your AI forgets you every morning.** You tell it your name, your work, your allergies, the way you like your answers — over and over. And when an AI finally *does* remember you, it remembers you inside someone else's walls: years of context that vanish with a policy change, a billing error, or a closed account.

MemoryVault is a **user-owned, portable memory** for AI. It ingests what you tell it, extracts durable facts about you, and serves them to *any* model over the Model Context Protocol — from a vault you can read, correct, and export as a file that's yours.

> Your phone number moves with you. Your photos move with you. Your memory should too.

---

## What it does

- **Remembers, verifiably.** An LLM extracts typed facts with a **confidence score** and **provenance** (which message, which model, when). Health / money / contact facts are gated to a **pending confirmation queue** — nothing high-stakes is trusted until you confirm it.
- **Stays current.** Facts have validity windows. "Moved to Toronto" **supersedes** "lives in Chennai" as a dated timeline instead of two contradictions sitting side by side.
- **Retrieves what's relevant.** Semantic vector search over your facts, ranked by similarity + recency + confidence + usage, returned as a **token-budgeted context pack** ready to prepend to any prompt.
- **Forgets on purpose.** Stale, low-confidence, unused facts decay out of the active set (archived, never destroyed) so the vault stays sharp over time.
- **Is yours.** Full-fidelity JSON export of every event and fact. Connect over hosted HTTP **or** a fully-local stdio MCP server. No lock-in.

## Architecture

Three layers — commodity shelves, a person-tuned librarian:

| Layer | What | Where |
|---|---|---|
| **L1** | Append-only event log (raw messages) | `backend/memory.py` |
| **L2** | Typed facts: confidence, provenance, temporal validity, supersession, status | `backend/memory.py`, `backend/extractor.py` |
| **L3** | Rebuildable vector index + person-tuned ranking | `backend/embeddings.py`, `backend/memory.py` |

**Stack:** FastAPI + MongoDB (Motor) · React + Tailwind dashboard · MCP over Streamable-HTTP and stdio · LLM extraction via the Emergent LLM key (Claude primary, Gemini fallback).

## Quick start

```bash
# Backend
cd backend
pip install -r requirements.txt
# set MONGO_URL, DB_NAME, EMERGENT_LLM_KEY in backend/.env
uvicorn server:app --host 0.0.0.0 --port 8001

# Frontend
cd frontend
yarn install && yarn start
```

## Configuration

| Env var | Purpose | Default |
|---|---|---|
| `MONGO_URL`, `DB_NAME` | MongoDB connection | — |
| `EMERGENT_LLM_KEY` | Fact extraction (and export object storage) | — |
| `EXTRACTION_MODEL` / `_PROVIDER` | Primary extractor | `claude-opus-4-5-20251101` / `anthropic` |
| `FALLBACK_MODEL` / `_PROVIDER` | Fallback extractor | `gemini-3-flash-preview` / `gemini` |

### Semantic embeddings (L3)

Retrieval ships with a safe, offline default and a real semantic backend you flip on with env vars:

| Env var | Purpose | Default |
|---|---|---|
| `EMBEDDING_BACKEND` | `hash` (offline, lexical) or `openai` (real semantic) | `hash` |
| `EMBEDDING_API_BASE` | Any OpenAI-compatible `/embeddings` endpoint | `https://api.openai.com/v1` |
| `EMBEDDING_API_KEY` | Key for that endpoint | — |
| `EMBEDDING_MODEL` | Embedding model | `text-embedding-3-small` |

`openai` mode works with OpenAI, Voyage, Together — **or a local Ollama / LM Studio server** (`EMBEDDING_API_BASE=http://localhost:11434/v1`) for a fully-owned, no-third-party setup.

> After changing the backend or model, re-embed existing facts once: `POST /api/index/rebuild`. Embedding dimensions differ per model; until you rebuild, the dimension guard keeps old and new vectors from being compared.

## Connect an AI client (MCP)

Sign up, grab your per-vault token from the dashboard's **Connect** page, then point any MCP client at your vault. Tools exposed: `search_memory`, `get_profile`, `save_memory`, `build_context_pack`, `confirm_fact`, `list_pending`.

- **Hosted:** `POST /api/mcp` (JSON-RPC 2.0 over Streamable-HTTP), `Authorization: Bearer mv_...`
- **Local:** `backend/mcp_stdio.py` (newline-delimited JSON-RPC over stdin/stdout, auth via `MCP_TOKEN` env) — drop it into `claude_desktop_config.json`.

## Benchmark

`backend/benchmark/harness.py` measures Recall@k, MRR and latency against a labeled dataset. The MemoryVault adapter runs live against the REST API; head-to-head adapters for mem0 / Zep are being wired up so results are directly comparable.

```bash
BENCH_BASE_URL=http://localhost:8001 python backend/benchmark/harness.py
```

## Status

Working: layered engine, LLM extraction with confidence + high-stakes gating, temporal supersession, decay, pending-confirmation flow, MCP (HTTP + stdio), JSON export + export bundles, web dashboard, rate limiting.

On the roadmap: real semantic embeddings on by default, head-to-head benchmark vs mem0/Zep (incl. supersession + negative cases), and a correction feedback loop that demotes facts which led to a fix.

## License

Not yet licensed — all rights reserved by the author for now.
