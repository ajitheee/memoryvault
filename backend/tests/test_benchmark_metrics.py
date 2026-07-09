"""Offline tests for the benchmark scoring logic (no network, no SDKs).

Verifies Recall/MRR and — critically — the freshness (supersession) metric:
a system that leaks a superseded value must score lower than one that doesn't.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmark"))

import harness as H


class ScriptedAdapter:
    """Returns canned search results per query, so metric math is deterministic."""
    name = "scripted"

    def __init__(self, script):
        self.script = script

    def ingest(self, text):
        pass

    def settle(self):
        pass

    def search(self, query, k):
        return self.script.get(query, [])[:k]


def test_first_rank_and_contains():
    assert H._first_rank(["nope", "has postgres here"], ["postgres"]) == 2
    assert H._first_rank(["nope"], ["postgres"]) == 0
    assert H._contains_any(["work at acme"], ["acme"]) is True
    assert H._contains_any(["work at globex"], ["acme"]) is False


def _perfect_script():
    # every query returns exactly its first relevant term, no forbidden terms
    return {q: [rel[0]] for q, rel, forb in H.QUERIES if rel}


def test_perfect_adapter_scores_max():
    m = H.evaluate(ScriptedAdapter(_perfect_script()), verbose=False)
    assert m["recall"] == 1.0
    assert m["mrr"] == 1.0
    assert m["freshness"] == 1.0  # new value present, old value absent


def test_stale_leak_tanks_freshness_not_recall():
    # A memory that keeps the superseded value: relevant IS present (recall ok)
    # but the old value leaks, so freshness must drop to 0.
    script = {}
    for q, rel, forb in H.QUERIES:
        if forb:
            script[q] = [forb[0], rel[0]]  # leak old value AND return new one
        elif rel:
            script[q] = [rel[0]]
    m = H.evaluate(ScriptedAdapter(script), verbose=False)
    assert m["recall"] == 1.0            # it still finds the right answer...
    assert m["freshness"] == 0.0         # ...but it never forgot the old one


def test_freshness_is_nan_when_no_forbidden_cases():
    # If the dataset had no supersession cases, freshness should be undefined.
    saved = H.QUERIES
    try:
        H.QUERIES = [("q", ["a"], [])]
        m = H.evaluate(ScriptedAdapter({"q": ["a"]}), verbose=False)
        assert math.isnan(m["freshness"])
    finally:
        H.QUERIES = saved


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
