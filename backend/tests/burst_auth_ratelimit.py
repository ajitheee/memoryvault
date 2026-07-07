"""Ad-hoc rate-limit burst test for /api/auth/login.
- Sends 32 login requests with wrong password (returns 401 normally).
- After 30 in a 60s window, subsequent requests must return 429 with Retry-After header.

Run AFTER all other tests: this locks the IP's auth bucket for ~60s.
"""
import os
import time
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or "https://ai-memory-hub-29.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

# Wait for any prior auth-window activity to age out.
print("Sleeping 65s to clear auth window...")
time.sleep(65)

results = []
first_429 = None
for i in range(1, 33):
    r = requests.post(f"{API}/auth/login",
                      json={"email": "does-not-exist@example.com", "password": "x"})
    results.append((i, r.status_code, r.headers.get("Retry-After")))
    if r.status_code == 429 and first_429 is None:
        first_429 = i
    if r.status_code == 429 and i > 30:
        break

# Summarize
codes = [c for _, c, _ in results]
print(f"Total requests: {len(results)}")
print(f"First 429 at request #: {first_429}")
print(f"Status codes: {codes}")
retry_hdrs = [rh for _, c, rh in results if c == 429]
print(f"Retry-After headers on 429s: {retry_hdrs[:5]}")

# Assertions
assert first_429 is not None, "Rate limit never triggered!"
assert first_429 >= 31, f"Rate limit triggered too early (at request {first_429}); expected >=31"
assert first_429 <= 32, f"Rate limit triggered too late (at request {first_429})"
# All requests before the first 429 must be 401 (invalid creds)
pre = codes[:first_429 - 1]
assert all(c == 401 for c in pre), f"Non-401 before 429 window: {pre}"
# Retry-After must be present on 429
assert retry_hdrs and all(rh is not None for rh in retry_hdrs), "Missing Retry-After header on 429"

print("\nRATE LIMIT AUTH BURST TEST: PASSED")
