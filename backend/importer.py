#!/usr/bin/env python3
"""One-time importer: SQLite `demo_vault.db` (prototype) -> MongoDB vault.

The prototype schema is not fixed, so this importer introspects tables and maps
columns heuristically:
  - An events/log table (has a text/content column + optional role/timestamp)
  - A facts table (has type/key/value + optional confidence/status)

Usage:
  python importer.py --db /path/to/demo_vault.db --vault <vault_id>
  python importer.py --db /path/to/demo_vault.db --email user@example.com
  python importer.py --db /path/to/demo_vault.db --email new@example.com --create --password secret
"""
import os
import sys
import uuid
import asyncio
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

from db import db  # noqa: E402
from embeddings import embed  # noqa: E402


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _columns(cur, table):
    cur.execute(f"PRAGMA table_info('{table}')")
    return [r[1] for r in cur.fetchall()]


def _pick(cols, *cands):
    low = {c.lower(): c for c in cols}
    for c in cands:
        if c in low:
            return low[c]
    return None


def _classify(cols):
    has = lambda *xs: any(_pick(cols, x) for x in xs)  # noqa: E731
    if (has("value") and (has("type", "fact_type") or has("key", "attribute"))) or has("confidence", "status"):
        return "facts"
    if has("text", "content", "message", "body"):
        return "events"
    return None


async def _resolve_vault(vault, email, create, password):
    if vault:
        return vault
    if email:
        user = await db.users.find_one({"email": email.lower()}, {"_id": 0})
        if user:
            return user["id"]
        if create:
            import bcrypt, secrets
            uid = str(uuid.uuid4())
            await db.users.insert_one({
                "id": uid, "email": email.lower(),
                "password_hash": bcrypt.hashpw((password or "changeme123").encode(), bcrypt.gensalt()).decode(),
                "name": email.split("@")[0], "role": "user",
                "mcp_token": "mv_" + secrets.token_urlsafe(32),
                "created_at": now_iso(),
            })
            print(f"Created vault for {email} (id={uid})")
            return uid
        raise SystemExit(f"No user with email {email}. Pass --create to make one.")
    raise SystemExit("Provide --vault or --email")


async def run(path, vault, email, create, password):
    if not os.path.exists(path):
        raise SystemExit(f"SQLite file not found: {path}")
    vault_id = await _resolve_vault(vault, email, create, password)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall() if not r[0].startswith("sqlite_")]

    ev_count = fact_count = 0
    for table in tables:
        cols = _columns(cur, table)
        kind = _classify(cols)
        if not kind:
            print(f"  · skip table '{table}' (unrecognized: {cols})")
            continue
        cur.execute(f"SELECT * FROM '{table}'")
        rows = cur.fetchall()
        if kind == "events":
            tc = _pick(cols, "text", "content", "message", "body")
            rc = _pick(cols, "role", "author", "speaker")
            ts = _pick(cols, "created_at", "timestamp", "ts", "time")
            for r in rows:
                await db.events.insert_one({
                    "id": str(uuid.uuid4()), "vault_id": vault_id,
                    "role": (r[rc] if rc else "user") or "user",
                    "text": r[tc] or "", "source": "import",
                    "created_at": str(r[ts]) if ts and r[ts] else now_iso(),
                })
                ev_count += 1
            print(f"  ✓ imported {len(rows)} events from '{table}'")
        elif kind == "facts":
            ty = _pick(cols, "type", "fact_type")
            ky = _pick(cols, "key", "attribute", "name")
            va = _pick(cols, "value", "val")
            cf = _pick(cols, "confidence", "conf")
            st = _pick(cols, "status", "state")
            for r in rows:
                ftype = (r[ty] if ty else "other") or "other"
                key = (r[ky] if ky else "fact") or "fact"
                value = str(r[va]) if va and r[va] is not None else ""
                if not value:
                    continue
                canonical = f"{ftype}: {str(key).replace('_', ' ')} = {value}"
                await db.facts.insert_one({
                    "id": str(uuid.uuid4()), "vault_id": vault_id,
                    "type": ftype, "key": key, "value": value,
                    "canonical_text": canonical,
                    "confidence": float(r[cf]) if cf and r[cf] is not None else 0.7,
                    "status": (r[st] if st else "active") or "active",
                    "high_stakes": False,
                    "provenance": {"event_id": None, "extracted_at": now_iso(), "model": "import", "role": "user"},
                    "valid_from": now_iso(), "valid_to": None,
                    "supersedes": [], "superseded_by": None,
                    "usage_count": 0, "last_used_at": None,
                    "embedding": embed(canonical),
                    "created_at": now_iso(), "updated_at": now_iso(),
                })
                fact_count += 1
            print(f"  ✓ imported facts from '{table}'")

    conn.close()
    print(f"\nDone. Imported {ev_count} events and {fact_count} facts into vault {vault_id}.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Path to demo_vault.db")
    ap.add_argument("--vault", help="Target vault id")
    ap.add_argument("--email", help="Target vault by user email")
    ap.add_argument("--create", action="store_true", help="Create the user if email not found")
    ap.add_argument("--password", help="Password for --create")
    args = ap.parse_args()
    asyncio.run(run(args.db, args.vault, args.email, args.create, args.password))
