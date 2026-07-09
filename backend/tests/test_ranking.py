"""Offline tests for the person-tuned ranking / feedback loop (no DB, no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ranking import combine_score


def _base(sim=0.8, conf=0.7, recency=0.5, helpful=0, corrected=0):
    return combine_score(sim, conf, recency, helpful, corrected)


def test_retrieval_alone_does_not_boost():
    # Score depends only on relevance + confirmed feedback — there is no usage
    # parameter, so merely being returned can't inflate a fact's own rank.
    import inspect
    params = inspect.signature(combine_score).parameters
    assert not any("usage" in p for p in params)


def test_helpful_lifts_a_fact():
    assert _base(helpful=5) > _base(helpful=0)


def test_correction_demotes_a_fact():
    assert _base(corrected=3) < _base(corrected=0)


def test_correction_outweighs_help():
    # One correction should hurt more than one helpful vote helps.
    assert _base(helpful=1, corrected=1) < _base(helpful=0, corrected=0)


def test_correction_reorders_against_similarity():
    # THE bug fix: a wrong fact that keeps getting retrieved used to win on
    # similarity alone. After repeated corrections it must fall behind a clean,
    # slightly-less-similar fact.
    wrong_but_similar = combine_score(0.90, 0.7, 0.5, helpful_count=0, correction_count=4)
    clean_less_similar = combine_score(0.78, 0.7, 0.5, helpful_count=0, correction_count=0)
    assert clean_less_similar > wrong_but_similar


def test_monotonic_in_similarity():
    assert combine_score(0.9, 0.5, 0.5, 0, 0) > combine_score(0.4, 0.5, 0.5, 0, 0)


def test_negative_counts_are_clamped():
    # Defensive: junk negative counters must not blow up the score.
    assert _base(helpful=-3, corrected=-3) == _base(helpful=0, corrected=0)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
