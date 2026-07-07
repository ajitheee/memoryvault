"""End-to-end backend tests for MemoryVault.
Covers: auth, ingestion+extraction, facts filtering, supersession,
pending flow, retrieval, context-pack, decay, export, vault isolation, MCP.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or "https://ai-memory-hub-29.preview.emergentagent.com"
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@memoryvault.dev"
ADMIN_PASSWORD = "admin123"


def _rand_email(prefix="test"):
    return f"TEST_{prefix}_{uuid.uuid4().hex[:8]}@example.com"


# -------- Fixtures --------
@pytest.fixture(scope="session")
def user_a():
    email = _rand_email("a")
    password = "Passw0rd!"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": password, "name": "User A"})
    assert r.status_code == 200, r.text
    d = r.json()
    return {"token": d["access_token"], "user": d["user"], "password": password}


@pytest.fixture(scope="session")
def user_b():
    email = _rand_email("b")
    password = "Passw0rd!"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": password, "name": "User B"})
    assert r.status_code == 200, r.text
    d = r.json()
    return {"token": d["access_token"], "user": d["user"], "password": password}


def hdr(u):
    return {"Authorization": f"Bearer {u['token']}", "Content-Type": "application/json"}


# -------- Auth --------
class TestAuth:
    def test_root_health(self):
        r = requests.get(f"{API}/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_register_and_me(self, user_a):
        r = requests.get(f"{API}/auth/me", headers=hdr(user_a))
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == user_a["user"]["email"]
        assert d["id"] == user_a["user"]["id"]
        assert d.get("mcp_token", "").startswith("mv_")

    def test_login_seeded_admin(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user"]["role"] == "admin"
        assert d["user"]["email"] == ADMIN_EMAIL
        assert "access_token" in d

    def test_login_wrong_password(self, user_a):
        r = requests.post(f"{API}/auth/login", json={"email": user_a["user"]["email"], "password": "wrong"})
        assert r.status_code == 401

    def test_me_no_token(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_duplicate_registration(self, user_a):
        r = requests.post(f"{API}/auth/register",
                          json={"email": user_a["user"]["email"], "password": "Passw0rd!", "name": "dup"})
        assert r.status_code == 400


# -------- Ingest / extraction --------
class TestIngestionAndExtraction:
    def test_save_memory_extracts_facts(self, user_a):
        text = ("My name is Alice Chen. I work at Acme Corp as a senior data engineer. "
                "My favorite programming language is Rust. "
                "I have a peanut allergy. "
                "My email is alice.chen@example.com.")
        r = requests.post(f"{API}/memory/save", headers=hdr(user_a),
                          json={"text": text, "role": "user"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["extracted"] >= 1, f"No facts extracted: {d}"
        assert "event_id" in d
        # store for later tests
        pytest.user_a_ingest = d
        # High-stakes gating: any health / contact fact should be pending
        for f in d["facts"]:
            if f["type"] in ("health", "contact"):
                assert f["status"] == "pending", f"High-stakes fact not pending: {f}"

    def test_facts_filter_all(self, user_a):
        r = requests.get(f"{API}/facts?status=all", headers=hdr(user_a))
        assert r.status_code == 200
        facts = r.json()
        assert isinstance(facts, list)
        assert len(facts) >= 1

    def test_facts_filter_active(self, user_a):
        r = requests.get(f"{API}/facts?status=active", headers=hdr(user_a))
        assert r.status_code == 200
        for f in r.json():
            assert f["status"] == "active"

    def test_facts_filter_pending(self, user_a):
        r = requests.get(f"{API}/facts?status=pending", headers=hdr(user_a))
        assert r.status_code == 200
        for f in r.json():
            assert f["status"] == "pending"


# -------- Supersession --------
class TestSupersession:
    def test_supersession_flow(self, user_b):
        # First fact
        r1 = requests.post(f"{API}/memory/save", headers=hdr(user_b),
                           json={"text": "My favorite programming language is Rust.", "role": "user"})
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        # find active preference fact with favorite_language key
        old_active = [f for f in d1["facts"]
                      if f["type"] == "preference" and "language" in f["key"] and f["status"] == "active"]
        # Extractor may pick a slightly different key; fall back to any active preference
        if not old_active:
            old_active = [f for f in d1["facts"] if f["status"] == "active"]
        assert old_active, f"No active fact created on first message: {d1}"

        # Second, superseding fact
        r2 = requests.post(f"{API}/memory/save", headers=hdr(user_b),
                           json={"text": "My favorite programming language is now Go.", "role": "user"})
        assert r2.status_code == 200
        time.sleep(0.5)

        # Check facts list
        r_all = requests.get(f"{API}/facts?status=all", headers=hdr(user_b))
        assert r_all.status_code == 200
        all_facts = r_all.json()
        # Find any superseded fact
        superseded = [f for f in all_facts if f["status"] == "superseded"]
        active_pref = [f for f in all_facts
                       if f["status"] == "active" and f["type"] == "preference"
                       and "go" in str(f["value"]).lower()]
        assert superseded, "Expected at least one superseded fact after conflicting update"
        assert active_pref, f"Expected active Go preference fact. Got: {[(f['type'],f['key'],f['value'],f['status']) for f in all_facts]}"


# -------- Pending confirmation flow --------
class TestPendingFlow:
    def test_confirm_and_reject(self, user_a):
        # Ingest something with high-stakes facts
        r = requests.post(f"{API}/memory/save", headers=hdr(user_a),
                          json={"text": "I have diabetes type 2. My phone number is 555-123-4567.",
                                "role": "user"})
        assert r.status_code == 200
        time.sleep(0.3)

        pend = requests.get(f"{API}/pending", headers=hdr(user_a))
        assert pend.status_code == 200
        pending = pend.json()
        assert len(pending) >= 1, "Expected pending facts (health/contact)"

        # Confirm first, reject second (if available)
        first = pending[0]
        cr = requests.post(f"{API}/facts/{first['id']}/confirm", headers=hdr(user_a))
        assert cr.status_code == 200
        assert cr.json()["status"] == "active"

        if len(pending) >= 2:
            second = pending[1]
            rj = requests.post(f"{API}/facts/{second['id']}/reject", headers=hdr(user_a))
            assert rj.status_code == 200
            # Verify archived
            gf = requests.get(f"{API}/facts/{second['id']}", headers=hdr(user_a))
            assert gf.status_code == 200
            assert gf.json()["status"] == "archived"

    def test_confirm_missing_fact(self, user_a):
        r = requests.post(f"{API}/facts/nonexistent-id/confirm", headers=hdr(user_a))
        assert r.status_code == 404


# -------- Retrieval + context pack --------
class TestRetrievalAndContextPack:
    def test_search_returns_scored_facts(self, user_a):
        r = requests.post(f"{API}/memory/search", headers=hdr(user_a),
                          json={"query": "what is my favorite language", "k": 5})
        assert r.status_code == 200
        results = r.json()
        assert isinstance(results, list)
        if results:
            f = results[0]
            assert "score" in f and "similarity" in f
            assert 0.0 <= f["score"] <= 1.0

    def test_context_pack_respects_budget(self, user_a):
        budget = 300
        r = requests.post(f"{API}/context-pack", headers=hdr(user_a),
                          json={"query": "personal profile", "token_budget": budget})
        assert r.status_code == 200
        d = r.json()
        assert d["token_budget"] == budget
        assert d["tokens_used"] <= budget + 5  # tiny slack for header rounding
        assert isinstance(d["context"], str)
        assert d["facts_included"] >= 0

    def test_context_pack_validation(self, user_a):
        r = requests.post(f"{API}/context-pack", headers=hdr(user_a),
                          json={"query": "x", "token_budget": 10})
        # 10 < 50 => 422
        assert r.status_code == 422


# -------- Decay & Export --------
class TestDecayAndExport:
    def test_decay(self, user_a):
        r = requests.post(f"{API}/decay", headers=hdr(user_a),
                          json={"max_age_days": 60, "min_confidence": 0.5})
        assert r.status_code == 200
        d = r.json()
        assert "archived" in d
        assert isinstance(d["archived"], int)

    def test_export(self, user_a):
        r = requests.get(f"{API}/export", headers=hdr(user_a))
        assert r.status_code == 200
        d = r.json()
        assert "facts" in d and "events" in d
        assert d["vault_id"] == user_a["user"]["id"]
        assert d["schema_version"] == 1


# -------- Vault isolation --------
class TestVaultIsolation:
    def test_user_a_cannot_see_user_b_facts(self, user_a, user_b):
        stats_a = requests.get(f"{API}/vault/stats", headers=hdr(user_a)).json()
        stats_b = requests.get(f"{API}/vault/stats", headers=hdr(user_b)).json()
        facts_a = requests.get(f"{API}/facts?status=all", headers=hdr(user_a)).json()
        facts_b = requests.get(f"{API}/facts?status=all", headers=hdr(user_b)).json()

        ids_a = {f["id"] for f in facts_a}
        ids_b = {f["id"] for f in facts_b}
        assert ids_a.isdisjoint(ids_b), "Facts leaked between vaults!"

        vault_ids_a = {f["vault_id"] for f in facts_a}
        vault_ids_b = {f["vault_id"] for f in facts_b}
        assert vault_ids_a <= {user_a["user"]["id"]}
        assert vault_ids_b <= {user_b["user"]["id"]}


# -------- MCP JSON-RPC --------
class TestMCP:
    def _rpc(self, method, params=None, headers=None, rpc_id=1):
        payload = {"jsonrpc": "2.0", "id": rpc_id, "method": method}
        if params is not None:
            payload["params"] = params
        return requests.post(f"{API}/mcp", json=payload, headers=headers or {})

    def test_initialize(self):
        r = self._rpc("initialize")
        assert r.status_code == 200
        d = r.json()
        assert d["result"]["protocolVersion"]
        assert d["result"]["serverInfo"]["name"] == "memoryvault"

    def test_tools_list_has_six_tools(self):
        r = self._rpc("tools/list", rpc_id=2)
        assert r.status_code == 200
        tools = r.json()["result"]["tools"]
        names = {t["name"] for t in tools}
        expected = {"search_memory", "get_profile", "save_memory",
                    "build_context_pack", "confirm_fact", "list_pending"}
        assert expected <= names
        assert len(tools) == 6

    def test_tools_call_without_auth_returns_401(self):
        r = self._rpc("tools/call", params={"name": "get_profile", "arguments": {}}, rpc_id=3)
        assert r.status_code == 401

    def test_tools_call_with_valid_token(self, user_a):
        info = requests.get(f"{API}/mcp/info", headers=hdr(user_a)).json()
        mcp_token = info["mcp_token"]
        assert mcp_token.startswith("mv_")

        # save_memory
        r = self._rpc("tools/call",
                      params={"name": "save_memory",
                              "arguments": {"text": "I live in Tokyo.", "role": "user"}},
                      headers={"Authorization": f"Bearer {mcp_token}"}, rpc_id=10)
        assert r.status_code == 200
        d = r.json()["result"]
        assert d["isError"] is False
        assert d["content"][0]["type"] == "text"
        # Content is JSON string
        import json as _j
        parsed = _j.loads(d["content"][0]["text"])
        assert "event_id" in parsed

        # search_memory
        r = self._rpc("tools/call",
                      params={"name": "search_memory",
                              "arguments": {"query": "where do I live", "k": 3}},
                      headers={"Authorization": f"Bearer {mcp_token}"}, rpc_id=11)
        assert r.status_code == 200
        assert r.json()["result"]["isError"] is False

        # build_context_pack
        r = self._rpc("tools/call",
                      params={"name": "build_context_pack",
                              "arguments": {"query": "profile summary", "token_budget": 500}},
                      headers={"Authorization": f"Bearer {mcp_token}"}, rpc_id=12)
        assert r.status_code == 200
        cp = _j.loads(r.json()["result"]["content"][0]["text"])
        assert "context" in cp and "tokens_used" in cp

    def test_notifications_return_202(self):
        r = self._rpc("notifications/initialized")
        assert r.status_code == 202

    def test_mcp_token_regenerate_invalidates_old(self, user_b):
        info = requests.get(f"{API}/mcp/info", headers=hdr(user_b)).json()
        old_token = info["mcp_token"]

        reg = requests.post(f"{API}/mcp/token/regenerate", headers=hdr(user_b))
        assert reg.status_code == 200
        new_token = reg.json()["mcp_token"]
        assert new_token != old_token
        assert new_token.startswith("mv_")

        # Old token should now fail
        r_old = self._rpc("tools/call",
                          params={"name": "get_profile", "arguments": {}},
                          headers={"Authorization": f"Bearer {old_token}"}, rpc_id=20)
        assert r_old.status_code == 401

        # New token should work
        r_new = self._rpc("tools/call",
                          params={"name": "get_profile", "arguments": {}},
                          headers={"Authorization": f"Bearer {new_token}"}, rpc_id=21)
        assert r_new.status_code == 200
        assert r_new.json()["result"]["isError"] is False
