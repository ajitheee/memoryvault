import uuid
import math
from datetime import datetime, timezone

from db import db
from embeddings import embed, cosine
from extractor import extract_facts, HIGH_STAKES_TYPES
from ranking import combine_score

ACTIVE_CONFIDENCE_THRESHOLD = 0.7


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.now(timezone.utc)


def approx_tokens(text: str) -> int:
    return max(1, math.ceil(len(text or "") / 4))


# ---------------- L1: Event log ----------------
async def add_event(vault_id: str, role: str, text: str, source: str = "api"):
    event = {
        "id": str(uuid.uuid4()),
        "vault_id": vault_id,
        "role": role,
        "text": text,
        "source": source,
        "created_at": now_iso(),
    }
    await db.events.insert_one(dict(event))
    return event


async def list_events(vault_id: str, limit: int = 200):
    return await db.events.find(
        {"vault_id": vault_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(limit)


# ---------------- L2: Typed facts ----------------
async def _supersede_existing(vault_id: str, ftype: str, key: str, new_id: str):
    """Mark active facts with the same (type, key) as superseded by new_id."""
    stamp = now_iso()
    olds = await db.facts.find({
        "vault_id": vault_id, "type": ftype, "key": key, "status": "active",
    }, {"_id": 0}).to_list(100)
    for old in olds:
        if old["id"] == new_id:
            continue
        await db.facts.update_one(
            {"id": old["id"]},
            {"$set": {
                "status": "superseded",
                "superseded_by": new_id,
                "valid_to": stamp,
                "updated_at": stamp,
            }},
        )
    return [o["id"] for o in olds if o["id"] != new_id]


async def create_fact(vault_id, ftype, key, value, confidence, high_stakes,
                      event_id, model, role="user"):
    fid = str(uuid.uuid4())
    stamp = now_iso()
    is_high = bool(high_stakes) or ftype in HIGH_STAKES_TYPES
    if is_high or confidence < ACTIVE_CONFIDENCE_THRESHOLD:
        status = "pending"
    else:
        status = "active"

    canonical = f"{ftype}: {key.replace('_', ' ')} = {value}"
    supersedes = []
    if status == "active":
        supersedes = await _supersede_existing(vault_id, ftype, key, fid)

    fact = {
        "id": fid,
        "vault_id": vault_id,
        "type": ftype,
        "key": key,
        "value": value,
        "canonical_text": canonical,
        "confidence": round(float(confidence), 3),
        "status": status,
        "high_stakes": is_high,
        "provenance": {
            "event_id": event_id,
            "extracted_at": stamp,
            "model": model,
            "role": role,
        },
        "valid_from": stamp,
        "valid_to": None,
        "supersedes": supersedes,
        "superseded_by": None,
        "usage_count": 0,
        "last_used_at": None,
        "helpful_count": 0,
        "correction_count": 0,
        "last_correction_at": None,
        "embedding": embed(canonical),
        "created_at": stamp,
        "updated_at": stamp,
    }
    await db.facts.insert_one(dict(fact))
    fact.pop("_id", None)
    return fact


async def save_memory(vault_id: str, text: str, role: str = "user", source: str = "api"):
    """Ingest raw text -> event log + LLM fact extraction."""
    event = await add_event(vault_id, role, text, source)
    extracted, model = await extract_facts(text, role)
    created = []
    for f in extracted:
        fact = await create_fact(
            vault_id, f["type"], f["key"], f["value"],
            f["confidence"], f["high_stakes"], event["id"], model, role,
        )
        created.append({k: v for k, v in fact.items() if k != "embedding"})
    pending = [f for f in created if f["status"] == "pending"]
    return {
        "event_id": event["id"],
        "extracted": len(created),
        "pending": len(pending),
        "model": model,
        "facts": created,
    }


# ---------------- L3: Retrieval ----------------
def _score(fact, query_vec, now):
    sim = cosine(fact.get("embedding") or [], query_vec)  # -1..1
    sim = (sim + 1) / 2  # 0..1
    conf = fact.get("confidence", 0.5)
    # recency: decay over ~30 days
    vf = _parse_iso(fact.get("valid_from") or fact.get("created_at"))
    age_days = max(0.0, (now - vf).total_seconds() / 86400.0)
    recency = math.exp(-age_days / 30.0)
    score = combine_score(sim, conf, recency,
                          fact.get("helpful_count", 0),
                          fact.get("correction_count", 0))
    return round(score, 4), round(sim, 4)


async def retrieve(vault_id: str, query: str, k: int = 8, mark_usage: bool = True):
    query_vec = embed(query)
    now = datetime.now(timezone.utc)
    facts = await db.facts.find(
        {"vault_id": vault_id, "status": "active"}, {"_id": 0}
    ).to_list(2000)
    scored = []
    for f in facts:
        s, sim = _score(f, query_vec, now)
        f2 = {k2: v for k2, v in f.items() if k2 != "embedding"}
        f2["score"] = s
        f2["similarity"] = sim
        scored.append(f2)
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:k]
    if mark_usage and top:
        stamp = now_iso()
        for f in top:
            await db.facts.update_one(
                {"id": f["id"]},
                {"$inc": {"usage_count": 1}, "$set": {"last_used_at": stamp}},
            )
    return top


async def build_context_pack(vault_id: str, query: str, token_budget: int = 1000):
    candidates = await retrieve(vault_id, query, k=50, mark_usage=True)
    profile = await get_profile(vault_id)
    lines = []
    used = 0
    header = "# User Memory Context\n"
    used += approx_tokens(header)
    included = []

    # Always try to include stable identity/preference profile first
    profile_lines = []
    for p in profile[:6]:
        line = f"- [{p['type']}] {p['key'].replace('_', ' ')}: {p['value']}"
        t = approx_tokens(line)
        if used + t > token_budget:
            break
        profile_lines.append(line)
        used += t
        included.append(p["id"])

    for f in candidates:
        if f["id"] in included:
            continue
        line = f"- [{f['type']}] {f['key'].replace('_', ' ')}: {f['value']} (conf {f['confidence']})"
        t = approx_tokens(line)
        if used + t > token_budget:
            break
        lines.append(line)
        used += t
        included.append(f["id"])

    parts = [header.strip()]
    if profile_lines:
        parts.append("## Profile\n" + "\n".join(profile_lines))
    if lines:
        parts.append("## Relevant Memory\n" + "\n".join(lines))
    context = "\n\n".join(parts)
    return {
        "query": query,
        "token_budget": token_budget,
        "tokens_used": approx_tokens(context),
        "facts_included": len(included),
        "context": context,
    }


async def get_profile(vault_id: str):
    facts = await db.facts.find({
        "vault_id": vault_id,
        "status": "active",
        "type": {"$in": ["identity", "preference", "work", "location", "skill"]},
    }, {"_id": 0, "embedding": 0}).sort("confidence", -1).to_list(100)
    return facts


# ---------------- Confirmation flow ----------------
async def confirm_fact(vault_id: str, fact_id: str):
    fact = await db.facts.find_one({"id": fact_id, "vault_id": vault_id}, {"_id": 0})
    if not fact:
        return None
    await _supersede_existing(vault_id, fact["type"], fact["key"], fact_id)
    stamp = now_iso()
    await db.facts.update_one(
        {"id": fact_id},
        {"$set": {"status": "active", "updated_at": stamp, "confirmed_at": stamp}},
    )
    return await db.facts.find_one({"id": fact_id}, {"_id": 0, "embedding": 0})


async def reject_fact(vault_id: str, fact_id: str):
    res = await db.facts.update_one(
        {"id": fact_id, "vault_id": vault_id},
        {"$set": {"status": "archived", "updated_at": now_iso(), "rejected": True}},
    )
    return res.modified_count > 0


# ---------------- Feedback loop (learned reranking) ----------------
VALID_VERDICTS = {"helpful", "correction"}


async def record_feedback(vault_id: str, fact_ids, verdict: str):
    """Record the outcome of using facts in a response (the feedback loop).

    verdict="helpful"    -> the served facts helped; nudge them up in future ranking.
    verdict="correction" -> the user corrected the answer those facts produced;
                            demote them so they surface less next time.

    Missing counters are created by $inc, so this works on pre-existing facts
    without a migration.
    """
    if verdict not in VALID_VERDICTS:
        return {"error": "verdict must be one of %s" % sorted(VALID_VERDICTS)}
    stamp = now_iso()
    if verdict == "helpful":
        update = {"$inc": {"helpful_count": 1}, "$set": {"last_used_at": stamp, "updated_at": stamp}}
    else:
        update = {"$inc": {"correction_count": 1}, "$set": {"last_correction_at": stamp, "updated_at": stamp}}
    updated = 0
    for fid in fact_ids or []:
        res = await db.facts.update_one({"id": fid, "vault_id": vault_id}, update)
        updated += res.modified_count
    return {"verdict": verdict, "updated": updated}


async def correct_fact(vault_id: str, fact_id: str, new_value: str = None):
    """Explicit correction: "that fact is wrong (it's actually X)".

    Always records the correction signal (demoting the fact). If `new_value` is
    given, also supersedes it with the corrected value via the normal create/
    supersede path, so the timeline stays consistent.
    """
    fact = await db.facts.find_one({"id": fact_id, "vault_id": vault_id}, {"_id": 0})
    if not fact:
        return None
    stamp = now_iso()
    await db.facts.update_one(
        {"id": fact_id},
        {"$inc": {"correction_count": 1}, "$set": {"last_correction_at": stamp, "updated_at": stamp}},
    )
    replacement = None
    if new_value:
        rep = await create_fact(
            vault_id, fact["type"], fact["key"], new_value,
            confidence=max(fact.get("confidence", 0.7), 0.9),
            high_stakes=fact.get("high_stakes", False),
            event_id=(fact.get("provenance") or {}).get("event_id"),
            model="user-correction", role="user",
        )
        replacement = {k: v for k, v in rep.items() if k != "embedding"}
    return {"corrected_id": fact_id, "replacement": replacement}


async def list_pending(vault_id: str):
    return await db.facts.find(
        {"vault_id": vault_id, "status": "pending"}, {"_id": 0, "embedding": 0}
    ).sort("created_at", -1).to_list(500)


async def list_facts(vault_id: str, status: str = None):
    q = {"vault_id": vault_id}
    if status and status != "all":
        q["status"] = status
    return await db.facts.find(q, {"_id": 0, "embedding": 0}).sort("updated_at", -1).to_list(2000)


async def get_fact(vault_id: str, fact_id: str):
    return await db.facts.find_one({"id": fact_id, "vault_id": vault_id}, {"_id": 0, "embedding": 0})


# ---------------- Decay / active forgetting ----------------
async def run_decay(vault_id: str, max_age_days: int = 60, min_confidence: float = 0.5):
    now = datetime.now(timezone.utc)
    facts = await db.facts.find(
        {"vault_id": vault_id, "status": "active"}, {"_id": 0}
    ).to_list(5000)
    archived = []
    for f in facts:
        vf = _parse_iso(f.get("valid_from") or f.get("created_at"))
        age = (now - vf).total_seconds() / 86400.0
        stale = age > max_age_days
        low_conf = f.get("confidence", 1.0) < min_confidence
        unused = f.get("usage_count", 0) == 0
        if stale and low_conf and unused:
            await db.facts.update_one(
                {"id": f["id"]},
                {"$set": {"status": "archived", "updated_at": now_iso(), "decayed": True}},
            )
            archived.append(f["id"])
    return {"archived": len(archived), "archived_ids": archived}


# ---------------- Stats + export ----------------
async def vault_stats(vault_id: str):
    counts = {}
    for st in ["active", "pending", "superseded", "archived"]:
        counts[st] = await db.facts.count_documents({"vault_id": vault_id, "status": st})
    counts["events"] = await db.events.count_documents({"vault_id": vault_id})
    counts["total_facts"] = await db.facts.count_documents({"vault_id": vault_id})
    # type breakdown for active
    pipeline = [
        {"$match": {"vault_id": vault_id, "status": "active"}},
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
    ]
    by_type = {}
    async for row in db.facts.aggregate(pipeline):
        by_type[row["_id"]] = row["count"]
    counts["by_type"] = by_type
    return counts


async def rebuild_index(vault_id: str):
    facts = await db.facts.find({"vault_id": vault_id}, {"_id": 0}).to_list(10000)
    for f in facts:
        await db.facts.update_one(
            {"id": f["id"]},
            {"$set": {"embedding": embed(f.get("canonical_text", "")), "updated_at": now_iso()}},
        )
    return {"rebuilt": len(facts)}


async def export_vault(vault_id: str):
    facts = await db.facts.find({"vault_id": vault_id}, {"_id": 0}).to_list(50000)
    events = await db.events.find({"vault_id": vault_id}, {"_id": 0}).to_list(50000)
    return {
        "vault_id": vault_id,
        "exported_at": now_iso(),
        "schema_version": 1,
        "facts": facts,
        "events": events,
    }
