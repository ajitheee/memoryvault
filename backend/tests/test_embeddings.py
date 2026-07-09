"""Offline unit tests for the pluggable embedding layer (no network, no Mongo)."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import embeddings as E


def test_default_backend_is_offline_hash():
    # Unset env => safe, offline default. Never silently requires a network key.
    assert E.BACKEND == "hash"
    assert E.semantic_enabled() is False


def test_hash_is_deterministic():
    assert E.embed("I moved to Toronto") == E.embed("I moved to Toronto")


def test_output_is_l2_normalized():
    v = E.embed("vegetarian, avoids dairy")
    assert abs(math.sqrt(sum(x * x for x in v)) - 1.0) < 1e-9


def test_empty_text_is_safe():
    v = E.embed("")
    assert len(v) == E.HASH_DIM
    assert all(x == 0.0 for x in v)


def test_cosine_bounds_and_self_similarity():
    v = E.embed("PostgreSQL for analytics")
    assert abs(E.cosine(v, v) - 1.0) < 1e-9
    assert -1.0001 <= E.cosine(E.embed("cello practice"), E.embed("fraud pipeline")) <= 1.0001


def test_cosine_guards_dimension_mismatch():
    # A leftover 384-dim vector vs a would-be 1536-dim vector must NOT be
    # compared on truncated overlap — it must read as 0 ("rebuild the index").
    assert E.cosine([0.1] * 384, [0.1] * 1536) == 0.0
    assert E.cosine([], [0.1, 0.2]) == 0.0


def test_shared_tokens_score_higher_than_unrelated():
    q = E.embed("database for analytics")
    related = E.embed("preference database postgresql analytics")
    unrelated = E.embed("learning to play the cello")
    assert E.cosine(q, related) > E.cosine(q, unrelated)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
