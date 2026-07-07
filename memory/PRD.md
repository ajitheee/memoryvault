# MemoryVault — PRD & Build Log

## Original Problem Statement
Turn a local-first AI memory prototype into a production-grade system: a standards-compliant
Model Context Protocol (MCP) server any AI client (Claude Desktop, Cursor, GPT apps) can connect
to, backed by FastAPI + MongoDB, LLM-based fact extraction, and embedding retrieval — plus a web
dashboard to own and manage a user vault.

## Architecture (implemented)
- **Backend** FastAPI (`/app/backend`): `server.py` (REST API), `mcp.py` (MCP JSON-RPC/Streamable-HTTP),
  `memory.py` (L1/L2/L3 engine), `extractor.py` (LLM extraction), `embeddings.py` (local cosine vector cache),
  `auth.py` (JWT + per-vault MCP tokens), `db.py` (Mongo).
- **Frontend** React + Tailwind brutalist dark dashboard (`/app/frontend/src`): Landing, Auth, and
  dashboard pages (Overview, Facts + FactDetail, Pending, Ingest, ContextPack, MCP Connect).
- **DB** MongoDB collections: `users`, `facts`, `events`.
- **LLM** Claude Opus 4.5 (`claude-opus-4-5-20251101`) primary, Gemini 3 Flash fallback, via Emergent LLM key.
- **Retrieval** Deterministic 384-dim hashing embedding + cosine; score = similarity + recency + confidence + usage. Rebuildable index.
- **Auth** Email+password JWT (Bearer in localStorage) + per-user opaque `mv_` MCP token.

## User Personas
- AI power users wanting continuity across ChatGPT/Claude/Gemini.
- Developers building agents needing persistent, trustworthy memory.
- Privacy-conscious users who want to own/export their memory.

## Core Requirements (static)
- Layered memory: L1 append-only events, L2 typed facts (temporal validity + supersession + status), L3 rebuildable index.
- LLM extractor with confidence + high-stakes (health/finance/contact) → PENDING gating.
- MCP tools: search_memory, get_profile, save_memory, build_context_pack, confirm_fact, list_pending.
- Active forgetting/decay, full JSON export, web dashboard.

## Implemented (2026-07-07)
- [x] Phase 1 — Core engine on MongoDB (events, typed facts, supersession, confidence, status, usage).
- [x] Phase 2 — MCP server: JSON-RPC 2.0 over HTTP (`POST /api/mcp`), per-vault Bearer token auth/isolation, 6 tools.
- [x] Phase 3 — LLM extractor (structured output + confidence + high-stakes gating) + embedding retrieval with rebuildable index.
- [x] Phase 4 — Web dashboard: auth, fact browser w/ provenance+timeline, pending queue, decay, context-pack preview, export, MCP connect page.
- Verified: 25/25 backend tests, 12/12 frontend flows (test_reports/iteration_1.json).

## Backlog / Remaining
- P2: Move object-storage upload to fully-async httpx (currently sync via asyncio.to_thread).
- P2: Distributed rate limiting (current limiter is per-process, fine for single container).
- P2: Expose bundle soft-delete endpoint; periodic prune of ratelimit buckets.
- P3: Head-to-head benchmark run vs real mem0/Zep (adapters stubbed, need API keys).

## Completed hardening + features (2026-07-07, iteration 2)
- [x] API rate limiting — sliding-window (auth 30/60s per IP, mcp 120/60s per IP, save 30/60s & context-pack 60/60s per vault). `ratelimit.py` + middleware.
- [x] Background decay scheduler — `decay_scheduler()` runs every DECAY_INTERVAL_SECONDS across all vaults.
- [x] Benchmark harness vs mem0/Zep — `benchmark/harness.py` (Recall@k, MRR, latency); MemoryVaultAdapter live, mem0/Zep adapter stubs.
- [x] Local stdio MCP transport — `mcp_stdio.py` (newline-delimited JSON-RPC over stdin/stdout, reuses HTTP tool dispatch, auth via MCP_TOKEN env).
- [x] Object-storage export bundles — `storage.py` + `/api/export/bundle` (create/list/download), served via backend with vault isolation.
- [x] `demo_vault.db` → Mongo importer — `importer.py` (heuristic SQLite schema introspection, CLI).
- Verified: 33/33 backend tests + rate-limit burst + Connect page UI (test_reports/iteration_2.json).

## Next Tasks
- Async storage client, distributed limiter, bundle lifecycle mgmt, live mem0/Zep benchmark comparison.
