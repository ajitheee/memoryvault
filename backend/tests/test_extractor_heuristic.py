"""Offline tests for the zero-key heuristic extractor (no LLM, no network).

These also prove the module IMPORTS without emergentintegrations installed —
the whole point of making the Emergent import lazy.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import extractor as X


def _facts(text):
    facts, model = X._run_heuristic(text, "user")
    assert model == "heuristic"
    return {f["key"]: f for f in facts}


def test_module_imports_without_emergent():
    # If the top-level import weren't lazy, importing extractor would already
    # have raised. Also: with no keys set, auto-resolve must pick heuristic.
    assert X._resolve_backend() in ("heuristic", "openai", "emergent")


def test_extracts_name_and_profession():
    f = _facts("My name is Sam Carter and I'm a data scientist.")
    assert f["full_name"]["value"] == "Sam Carter"
    assert f["profession"]["value"] == "data scientist"


def test_diet_and_allergy_high_stakes():
    f = _facts("I'm vegetarian and avoid dairy when I can.")
    assert f["diet"]["value"] == "vegetarian"
    f2 = _facts("I'm allergic to shellfish.")
    assert f2["allergy"]["value"] == "shellfish"
    assert f2["allergy"]["high_stakes"] is True  # health -> pending confirmation


def test_supersession_pair_home_city():
    # The classic demo: same stable key across two messages -> L2 can supersede.
    assert _facts("I live in Chennai.")["home_city"]["value"] == "Chennai"
    assert _facts("I moved to Toronto last year.")["home_city"]["value"] == "Toronto"


def test_supersession_pair_employer():
    assert _facts("I work at Acme Corp.")["employer"]["value"] == "Acme Corp"
    assert _facts("I left Acme Corp — I now work at Globex.")["employer"]["value"] == "Globex"


def test_no_facts_from_chitchat():
    facts, _ = X._run_heuristic("What time is the meeting tomorrow?", "user")
    assert facts == []


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
