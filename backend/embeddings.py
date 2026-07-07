import re
import math
import hashlib

DIM = 384


def _tokens(text: str):
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def embed(text: str):
    """Deterministic, dependency-free bag-of-words hashing embedding.

    Rebuildable from canonical text at any time. Uses signed hashing into a
    fixed-dimension vector, then L2-normalizes so cosine == dot product.
    """
    vec = [0.0] * DIM
    toks = _tokens(text)
    if not toks:
        return vec
    for tok in toks:
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        idx = h % DIM
        sign = 1.0 if (h >> 12) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a, b) -> float:
    if not a or not b:
        return 0.0
    return sum(x * y for x, y in zip(a, b))
