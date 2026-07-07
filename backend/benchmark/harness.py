#!/usr/bin/env python3
"""MemoryVault benchmark harness (vs mem0 / Zep).

Runs a small, reproducible memory eval: ingest labeled messages, then issue
queries with known relevant facts, and measure Recall@k, MRR and latency.

MemoryVaultAdapter talks to the live REST API. Mem0Adapter / ZepAdapter are
stubs — plug in the respective SDKs + API keys to run a head-to-head. The
metric code is shared so results are directly comparable.

Usage:
  BENCH_BASE_URL=http://localhost:8001 python harness.py
  BENCH_BASE_URL=http://localhost:8001 python harness.py --adapter memoryvault
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

# --- Labeled dataset: (message) ingested, then (query, [relevant substrings]) ---
INGEST = [
    "My name is Sam Carter and I'm a data scientist based in Toronto.",
    "I strongly prefer PostgreSQL over MySQL for analytics workloads.",
    "I'm learning to play the cello and practice every morning.",
    "My sister Mia is a pediatric nurse in Vancouver.",
    "I switched from Python to Rust for my performance-critical services.",
    "I'm vegetarian and avoid dairy when I can.",
    "My main project this quarter is a real-time fraud detection pipeline.",
    "I use a mechanical keyboard with brown switches.",
]

QUERIES = [
    ("What database does the user like for analytics?", ["postgres", "postgresql"]),
    ("Where does the user live?", ["toronto"]),
    ("What instrument is the user learning?", ["cello"]),
    ("What is the user's diet?", ["vegetarian", "dairy"]),
    ("What language does the user use for performance-critical code?", ["rust"]),
    ("What is the user's current main project?", ["fraud"]),
    ("What is the user's profession?", ["data scientist"]),
]


class MemoryVaultAdapter:
    name = "MemoryVault"

    def __init__(self):
        self.s = requests.Session()
        email = f"bench_{uuid.uuid4().hex[:8]}@bench.dev"
        r = self.s.post(f"{BASE_URL}/api/auth/register",
                        json={"email": email, "password": "benchpass123", "name": "Bench"})
        r.raise_for_status()
        self.token = r.json()["access_token"]
        self.s.headers.update({"Authorization": f"Bearer {self.token}"})

    def ingest(self, text):
        self.s.post(f"{BASE_URL}/api/memory/save", json={"text": text, "role": "user"}).raise_for_status()

    def search(self, query, k):
        r = self.s.post(f"{BASE_URL}/api/memory/search", json={"query": query, "k": k})
        r.raise_for_status()
        return [f"{f['key']} {f['value']}".lower() for f in r.json()]


class Mem0Adapter:
    name = "mem0"

    def __init__(self):
        raise NotImplementedError(
            "Install `mem0ai`, set MEM0_API_KEY, and implement ingest/search here. "
            "See https://docs.mem0.ai — the metric code below is adapter-agnostic."
        )


class ZepAdapter:
    name = "Zep"

    def __init__(self):
        raise NotImplementedError(
            "Install `zep-python`, set ZEP_API_KEY, and implement ingest/search here. "
            "See https://docs.getzep.com — the metric code below is adapter-agnostic."
        )


ADAPTERS = {"memoryvault": MemoryVaultAdapter, "mem0": Mem0Adapter, "zep": ZepAdapter}


def _hit_rank(results, relevant):
    for i, r in enumerate(results):
        if any(sub in r for sub in relevant):
            return i + 1
    return 0


def run(adapter_key):
    cls = ADAPTERS[adapter_key]
    adapter = cls()
    print(f"\n=== Benchmark: {adapter.name} @ {BASE_URL} ===")

    t0 = time.time()
    for msg in INGEST:
        adapter.ingest(msg)
    ingest_ms = (time.time() - t0) / len(INGEST) * 1000
    print(f"Ingested {len(INGEST)} messages · avg {ingest_ms:.0f} ms/msg\n")

    recalls, rr, latencies = [], [], []
    for query, relevant in QUERIES:
        s = time.time()
        results = adapter.search(query, K)
        latencies.append((time.time() - s) * 1000)
        rank = _hit_rank(results, relevant)
        recalls.append(1.0 if rank and rank <= K else 0.0)
        rr.append(1.0 / rank if rank else 0.0)
        mark = "✓" if rank else "✗"
        print(f"  {mark} rank={rank or '-':<3} | {query}")

    print("\n--- Results ---")
    print(f"  Recall@{K}: {statistics.mean(recalls):.2f}")
    print(f"  MRR:       {statistics.mean(rr):.2f}")
    print(f"  Search latency: p50 {statistics.median(latencies):.0f} ms · "
          f"max {max(latencies):.0f} ms")
    print(f"  Queries: {len(QUERIES)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="memoryvault", choices=list(ADAPTERS))
    args = ap.parse_args()
    try:
        run(args.adapter)
    except NotImplementedError as e:
        print(f"[{args.adapter}] {e}")
        sys.exit(2)
