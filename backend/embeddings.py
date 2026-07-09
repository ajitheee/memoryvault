"""Embeddings for MemoryVault's L3 retrieval index.

Two backends behind one `embed()` call:

  * "hash"  (default) — a deterministic, dependency-free bag-of-words hash.
              Offline, zero-cost, and rebuildable — but LEXICAL, not semantic:
              it only matches on shared tokens. Kept as the always-available
              fallback so the app never hard-depends on a network service.

  * "openai" — a real semantic embedding via any OpenAI-compatible /embeddings
              endpoint (OpenAI, Voyage, Together, or a LOCAL Ollama / LM Studio
              server). This is what makes retrieval find what's *relevant*, not
              just what shares words.

Select the backend with env vars (all optional — unset == "hash", safe default):

  EMBEDDING_BACKEND  = hash | openai              (default: hash)
  EMBEDDING_API_BASE = https://api.openai.com/v1  (or http://localhost:11434/v1 for Ollama)
  EMBEDDING_API_KEY  = sk-...                      (any non-empty value for local servers)
  EMBEDDING_MODEL    = text-embedding-3-small
  EMBEDDING_TIMEOUT  = 15                          (seconds)

IMPORTANT: embedding dimensions differ per backend/model (hash=384,
text-embedding-3-small=1536, ...). After changing the backend or model you MUST
re-embed existing facts:  POST /api/index/rebuild  (memory.rebuild_index).
Until then, `cosine()` safely returns 0.0 for any dimension-mismatched pair
rather than silently comparing truncated vectors.
"""
import os
import re
import math
import hashlib
import logging
from functools import lru_cache

import requests

logger = logging.getLogger(__name__)

HASH_DIM = 384

BACKEND = os.environ.get("EMBEDDING_BACKEND", "hash").lower()
API_BASE = os.environ.get("EMBEDDING_API_BASE", "https://api.openai.com/v1").rstrip("/")
API_KEY = os.environ.get("EMBEDDING_API_KEY", "")
MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
TIMEOUT = float(os.environ.get("EMBEDDING_TIMEOUT", "15"))

# Process-level circuit breaker: if the remote backend errors once, stop
# hammering it for the rest of this process and degrade to the hash. Cleared
# only by a restart (after fixing config) + an index rebuild.
_degraded = False


def _tokens(text: str):
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _normalize(vec):
    """L2-normalize so cosine similarity reduces to a plain dot product."""
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _hash_embed(text: str):
    """Deterministic signed-hashing bag-of-words vector. Lexical only."""
    vec = [0.0] * HASH_DIM
    toks = _tokens(text)
    if not toks:
        return vec
    for tok in toks:
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        idx = h % HASH_DIM
        sign = 1.0 if (h >> 12) % 2 == 0 else -1.0
        vec[idx] += sign
    return _normalize(vec)


def _openai_embed(text: str):
    """Real semantic embedding via an OpenAI-compatible /embeddings endpoint."""
    resp = requests.post(
        f"{API_BASE}/embeddings",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"model": MODEL, "input": text or " "},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    vec = resp.json()["data"][0]["embedding"]
    return _normalize([float(x) for x in vec])


def semantic_enabled() -> bool:
    """True when a real semantic backend is configured and hasn't degraded."""
    return BACKEND == "openai" and bool(API_KEY) and not _degraded


@lru_cache(maxsize=4096)
def _embed_cached(text: str):
    global _degraded
    if BACKEND == "openai" and API_KEY and not _degraded:
        try:
            return tuple(_openai_embed(text))
        except Exception as e:  # network/quota/config — degrade, don't crash retrieval
            _degraded = True
            logger.warning(
                "Embedding backend '%s' failed (%s). Degrading to offline hash for this "
                "process. Fix EMBEDDING_* env, restart, then POST /api/index/rebuild to "
                "restore semantic search.", MODEL, e,
            )
    return tuple(_hash_embed(text))


def embed(text: str):
    """Return an L2-normalized embedding for `text`.

    Semantic when a backend is configured, deterministic hash otherwise. Cached
    per-process so repeated identical text (e.g. a hot query) costs one call.
    """
    return list(_embed_cached(text or ""))


def cosine(a, b) -> float:
    """Cosine similarity of two L2-normalized vectors.

    Guards against dimension mismatch (e.g. hash-384 vs semantic-1536 left over
    from a backend switch) by returning 0.0 instead of comparing truncated
    vectors — that signals "rebuild the index" rather than producing garbage.
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))
