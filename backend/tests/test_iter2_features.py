"""Iteration 2 backend tests for MemoryVault:
- Object-storage export bundles (create, list, download, vault isolation)
- Per-vault rate limiting sanity (a small number of calls are NOT limited)
- Instant /api/export still works (regression)

NOTE: The 30/60s burst rate-limit tests for /api/auth and /api/memory/save are
intentionally exercised by a separate ad-hoc script (see test_reports notes),
because they consume the shared IP quota and slow LLM calls, respectively.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or "https://ai-memory-hub-29.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _rand_email(prefix="i2"):
    return f"TEST_{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _register(prefix):
    email = _rand_email(prefix)
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "password": "Passw0rd!", "name": prefix})
    assert r.status_code == 200, r.text
    d = r.json()
    return {"token": d["access_token"], "user": d["user"]}


@pytest.fixture(scope="module")
def user_x():
    return _register("x")


@pytest.fixture(scope="module")
def user_y():
    return _register("y")


def hdr(u):
    return {"Authorization": f"Bearer {u['token']}", "Content-Type": "application/json"}


# ---------- Export bundles ----------
class TestExportBundles:
    def test_instant_export_regression(self, user_x):
        """GET /api/export returns full facts+events JSON."""
        r = requests.get(f"{API}/export", headers=hdr(user_x))
        assert r.status_code == 200, r.text
        d = r.json()
        assert "facts" in d and "events" in d
        assert d["vault_id"] == user_x["user"]["id"]
        assert d["schema_version"] == 1
        assert isinstance(d["facts"], list)
        assert isinstance(d["events"], list)

    def test_create_bundle_returns_metadata(self, user_x):
        """POST /api/export/bundle uploads JSON and returns {id, storage_path, size, facts, events}."""
        # Seed a fact so bundle has content (optional; empty vault also OK)
        requests.post(f"{API}/memory/save", headers=hdr(user_x),
                      json={"text": "My name is Xavier and I like coffee.", "role": "user"})

        r = requests.post(f"{API}/export/bundle", headers=hdr(user_x))
        assert r.status_code == 200, r.text
        d = r.json()
        assert "id" in d and isinstance(d["id"], str) and len(d["id"]) >= 8
        assert "storage_path" in d and d["storage_path"]
        assert "size" in d and isinstance(d["size"], int) and d["size"] > 0
        assert "facts" in d and isinstance(d["facts"], int)
        assert "events" in d and isinstance(d["events"], int)
        assert d["vault_id"] == user_x["user"]["id"]
        assert "_id" not in d  # Mongo _id must be excluded
        pytest.user_x_bundle = d

    def test_list_bundles_newest_first(self, user_x):
        # Create a 2nd bundle to verify ordering
        time.sleep(1.1)
        r2 = requests.post(f"{API}/export/bundle", headers=hdr(user_x))
        assert r2.status_code == 200
        second = r2.json()

        r = requests.get(f"{API}/export/bundles", headers=hdr(user_x))
        assert r.status_code == 200
        bundles = r.json()
        assert isinstance(bundles, list)
        assert len(bundles) >= 2
        # Newest first: created_at descending
        cas = [b["created_at"] for b in bundles]
        assert cas == sorted(cas, reverse=True), f"Bundles not sorted newest-first: {cas}"
        # The most recent should match `second`
        assert bundles[0]["id"] == second["id"]
        # All belong to user_x
        for b in bundles:
            assert b["vault_id"] == user_x["user"]["id"]
            assert "_id" not in b

    def test_download_bundle_returns_full_json(self, user_x):
        bundle = getattr(pytest, "user_x_bundle", None)
        assert bundle, "prior test_create_bundle must have run"
        r = requests.get(f"{API}/export/bundle/{bundle['id']}/download", headers=hdr(user_x))
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        body = r.json()
        assert "facts" in body and "events" in body
        assert body["vault_id"] == user_x["user"]["id"]

    def test_bundle_vault_isolation(self, user_x, user_y):
        """User_y cannot fetch user_x's bundle (returns 404)."""
        bundle = getattr(pytest, "user_x_bundle", None)
        assert bundle, "prior test_create_bundle must have run"
        r = requests.get(f"{API}/export/bundle/{bundle['id']}/download", headers=hdr(user_y))
        assert r.status_code == 404, f"Vault isolation broken! Got {r.status_code}: {r.text}"

        # And user_y's bundle list must NOT include user_x's bundle
        ry = requests.get(f"{API}/export/bundles", headers=hdr(user_y))
        assert ry.status_code == 200
        y_ids = {b["id"] for b in ry.json()}
        assert bundle["id"] not in y_ids

    def test_download_unknown_bundle_404(self, user_x):
        r = requests.get(f"{API}/export/bundle/nonexistent-abc-123/download",
                         headers=hdr(user_x))
        assert r.status_code == 404


# ---------- Rate limit sanity (does NOT burst 30) ----------
class TestRateLimitSanity:
    def test_normal_context_pack_calls_not_limited(self, user_y):
        """A small burst of /context-pack calls (well under 60/60s) must all succeed."""
        for i in range(5):
            r = requests.post(f"{API}/context-pack", headers=hdr(user_y),
                              json={"query": f"test {i}", "token_budget": 200})
            assert r.status_code == 200, f"call {i} got {r.status_code}: {r.text}"

    def test_normal_search_calls_not_limited(self, user_y):
        """/memory/search has no per-vault limit → many calls work."""
        for i in range(6):
            r = requests.post(f"{API}/memory/search", headers=hdr(user_y),
                              json={"query": f"q{i}", "k": 3})
            assert r.status_code == 200
