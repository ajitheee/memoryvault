#!/usr/bin/env python3
"""MemoryVault benchmark harness — head-to-head vs mem0 / Zep.

Ingests an ORDERED script of labeled messages (some of which supersede earlier
ones), then issues queries and measures three things:

  * Recall@k / MRR  — does the relevant fact come back at all?
  * Freshness       — after "moved to Toronto", does a location query return
                      Toronto and NOT Chennai? This is the supersession edge
                      generic RAG memory tends to fail: it keeps both.
  * Latency         — p50 / max search time.

All three adapters share the same dataset and metric code, so numbers are
directly comparable. mem0 / Zep SDKs are imported lazily inside their adapters,
so this runs for MemoryVault alone with neither package installed.

Usage:
  # MemoryVault only (needs the API running):
  BENCH_BASE_URL=http://localhost:8001 python harness.py

  # Head-to-head (needs keys + `pip install mem0ai zep-cloud`):
  BENCH_BASE_URL=http://localhost:8001 \
  MEM0_API_KEY=... ZEP_API_KEY=... python harness.py --adapter all

Env:
  BENCH_BASE_URL        MemoryVault API base (default http://localhost:8001)
  MEM0_API_KEY          mem0 platform key (for the mem0 adapter)
  ZEP_API_KEY           Zep Cloud key (for the zep adapter)
  BENCH_ZEP_SETTLE      seconds to wait for Zep's async graph to build (default 15)
"""
import os
import sys
import time
import uuid
import argparse
import statistics

import requests

BASE_URL = os.environ.get("BENCH_BASE_URL", "http://localhost:8001").rstrip("/")
K = 5

# --- Ordered ingest script. Order matters: later lines supersede earlier ones. ---
INGEST = [
    "My name is Sam Carter and I'm a data scientist.",
    "I strongly prefer PostgreSQL over MySQL for analytics workloads.",
    "I'm learning to play the cello and practice every morning.",
    "My sister Mia is a pediatric nurse in Vancouver.",
    "I'm vegetarian and avoid dairy when I can.",
    "My main project this quarter is a real-time fraud detection pipeline.",
    "I use a mechanical keyboard with brown switches.",
    # --- supersession pair A: employer changes ---
    "I work at Acme Corp.",
    "I left Acme Corp — I now work at Globex.",
    # --- supersession pair B: location changes ---
    "I live in Chennai.",
    "I moved to Toronto last year.",
]

# (query, must-appear substrings, must-NOT-appear substrings)
QUERIES = [
    ("What database does the user like for analytics?", ["postgres", "postgresql"], []),
    ("What instrument is the user learning?", ["cello"], []),
    ("What is the user's diet?", ["vegetarian", "dairy"], []),
    ("What is the user's current main project?", ["fraud"], []),
    ("What is the user's profession?", ["data scientist", "data-scientist"], []),
    # supersession / freshness cases: new value required, old value forbidden
    ("Where does the user work now?", ["globex"], ["acme"]),
    ("Where does the user live now?", ["toronto"], ["chennai"]),
]


# ============================ Adapters ============================
class MemoryVaultAdapter:
    name = "MemoryVault"

    def __init__(self):
        self.s = requests.Session()
        email = f"bench_{uuid.uuid4().hex[:8]}@bench.dev"
        r = self.s.post(f"{BASE_URL}/api/auth/register",
                        json={"email": email, "password": "benchpass123", "name": "Bench"})
        r.raise_for_status()
        self.s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})

    def ingest(self, text):
        self.s.post(f"{BASE_URL}/api/memory/save",
                    json={"text": text, "role": "user"}).raise_for_status()

    def settle(self):
        pass  # facts are queryable immediately

    def search(self, query, k):
        r = self.s.post(f"{BASE_URL}/api/memory/search", json={"query": query, "k": k})
        r.raise_for_status()
        return [f"{f.get('key', '')} {f.get('value', '')}".lower() for f in r.json()]


class Mem0Adapter:
    name = "mem0"

    def __init__(self):
        key = os.environ.get("MEM0_API_KEY")
        if not key:
            raise RuntimeError("Set MEM0_API_KEY to run the mem0 adapter.")
        try:
            from mem0 import MemoryClient  # pip install mem0ai
        except ImportError as e:
            raise RuntimeError("pip install mem0ai to run the mem0 adapter.") from e
        self.client = MemoryClient(api_key=key)
        self.user_id = f"bench_{uuid.uuid4().hex[:8]}"

    def ingest(self, text):
        self.client.add(messages=[{"role": "user", "content": text}], user_id=self.user_id)

    def settle(self):
        time.sleep(2)

    def search(self, query, k):
        res = self.client.search(query, user_id=self.user_id, limit=k)
        items = res.get("results", res) if isinstance(res, dict) else res
        out = []
        for m in (items or [])[:k]:
            text = m.get("memory") or m.get("text") or "" if isinstance(m, dict) else str(m)
            out.append(str(text).lower())
        return out


class ZepAdapter:
    name = "Zep"

    def __init__(self):
        key = os.environ.get("ZEP_API_KEY")
        if not key:
            raise RuntimeError("Set ZEP_API_KEY to run the Zep adapter.")
        try:
            from zep_cloud.client import Zep  # pip install zep-cloud
            from zep_cloud import Message
        except ImportError as e:
            raise RuntimeError("pip install zep-cloud to run the Zep adapter.") from e
        self._Message = Message
        self.client = Zep(api_key=key)
        self.user_id = f"bench_{uuid.uuid4().hex[:8]}"
        self.thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        self.client.user.add(user_id=self.user_id)
        self.client.thread.create(thread_id=self.thread_id, user_id=self.user_id)

    def ingest(self, text):
        self.client.thread.add_messages(
            thread_id=self.thread_id,
            messages=[self._Message(name="Bench", role="user", content=text)],
        )

    def settle(self):
        # Zep builds the knowledge graph asynchronously — give it time.
        time.sleep(float(os.environ.get("BENCH_ZEP_SETTLE", "15")))

    def search(self, query, k):
        res = self.client.graph.search(user_id=self.user_id, query=query, limit=k, scope="edges")
        edges = getattr(res, "edges", None) or []
        return [str(getattr(e, "fact", "") or "").lower() for e in edges][:k]


ADAPTERS = {"memoryvault": MemoryVaultAdapter, "mem0": Mem0Adapter, "zep": ZepAdapter}


# ============================ Metrics ============================
def _first_rank(results, substrs):
    """1-indexed rank of the first result containing any substring, else 0."""
    for i, r in enumerate(results):
        if any(sub in r for sub in substrs):
            return i + 1
    return 0


def _contains_any(results, substrs):
    return any(any(sub in r for sub in substrs) for r in results)


def evaluate(adapter, k=K, verbose=True):
    t0 = time.time()
    for msg in INGEST:
        adapter.ingest(msg)
    ingest_ms = (time.time() - t0) / len(INGEST) * 1000
    adapter.settle()

    recalls, rr, latencies, fresh = [], [], [], []
    if verbose:
        print(f"\n=== {adapter.name} @ ingest {ingest_ms:.0f} ms/msg ===")
    for query, relevant, forbidden in QUERIES:
        s = time.time()
        results = adapter.search(query, k)
        latencies.append((time.time() - s) * 1000)

        rank = _first_rank(results, relevant) if relevant else 0
        found = bool(rank and rank <= k)
        recalls.append(1.0 if found else 0.0)
        rr.append(1.0 / rank if rank else 0.0)

        stale_leaked = _contains_any(results, forbidden) if forbidden else False
        if forbidden:
            # "fresh" == new value present AND old (superseded) value absent
            fresh.append(1.0 if (found and not stale_leaked) else 0.0)

        if verbose:
            mark = "✓" if found else "✗"
            tail = "  ⚠ STALE LEAK" if stale_leaked else ""
            print(f"  {mark} rank={rank or '-':<3} | {query}{tail}")

    return {
        "adapter": adapter.name,
        "recall": statistics.mean(recalls),
        "mrr": statistics.mean(rr),
        "freshness": statistics.mean(fresh) if fresh else float("nan"),
        "p50_ms": statistics.median(latencies),
        "max_ms": max(latencies),
    }


def _print_summary(rows):
    print(f"\n{'Adapter':<14}{'Recall@'+str(K):<10}{'MRR':<8}{'Freshness':<11}{'p50 ms':<9}{'max ms':<8}")
    print("-" * 60)
    for r in rows:
        fresh = "n/a" if r["freshness"] != r["freshness"] else f"{r['freshness']:.2f}"  # NaN check
        print(f"{r['adapter']:<14}{r['recall']:<10.2f}{r['mrr']:<8.2f}{fresh:<11}"
              f"{r['p50_ms']:<9.0f}{r['max_ms']:<8.0f}")
    print("\nFreshness = supersession correctness: after an update, the new value is "
          "returned and the old one is gone. Higher is better.")


def run(adapter_key):
    keys = list(ADAPTERS) if adapter_key == "all" else [adapter_key]
    rows = []
    for key in keys:
        try:
            rows.append(evaluate(ADAPTERS[key]()))
        except Exception as e:
            print(f"\n[{key}] skipped: {e}")
    if rows:
        _print_summary(rows)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="memoryvault",
                    choices=list(ADAPTERS) + ["all"])
    args = ap.parse_args()
    run(args.adapter)
