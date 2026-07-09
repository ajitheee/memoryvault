"""Person-tuned ranking for MemoryVault retrieval.

Pure functions only — no I/O, no DB — so the ranking policy is inspectable and
unit-testable on its own. `memory._score` feeds normalized signals in here.
"""
import math


def combine_score(sim, conf, recency, helpful_count, correction_count):
    """Blend retrieval signals into a single ranking score.

    `sim`, `conf`, `recency` are pre-normalized to [0, 1]. The last two terms
    are the *learned feedback* signal — the compounding advantage:

      - `helpful_count`     facts an AI client confirmed were useful -> gentle lift
      - `correction_count`  facts that were served and then led the user to
                            correct the answer -> penalty, weighted ~2x the lift
                            (a wrong memory hurts more than a right one helps)

    Crucially, *being retrieved* is not itself a positive signal — so a
    wrong-but-frequently-returned fact can't inflate its own rank the way a raw
    usage counter would. Only confirmed outcomes move a fact.
    """
    helpful = math.tanh(max(0, helpful_count) / 4.0)        # [0, 1)
    corrected = math.tanh(max(0, correction_count) / 2.0)   # [0, 1)
    return 0.55 * sim + 0.15 * conf + 0.10 * recency + 0.10 * helpful - 0.20 * corrected
