import time
from collections import defaultdict, deque

from fastapi import HTTPException

_buckets = defaultdict(deque)


def check(key: str, limit: int, window_seconds: int):
    """Sliding-window in-memory rate limiter. Raises 429 when exceeded."""
    now = time.time()
    dq = _buckets[key]
    cutoff = now - window_seconds
    while dq and dq[0] <= cutoff:
        dq.popleft()
    if len(dq) >= limit:
        retry = int(dq[0] + window_seconds - now) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({limit}/{window_seconds}s). Retry in {retry}s.",
            headers={"Retry-After": str(retry)},
        )
    dq.append(now)


def client_ip(request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
