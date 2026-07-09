"""Fact extraction — provider-agnostic so it runs anywhere, not just on Emergent.

Backends (env EXTRACTION_BACKEND, default "auto"):

  * emergent  — Emergent LLM key via emergentintegrations (imported LAZILY, so
                this module loads fine when the package isn't installed).
  * openai    — any OpenAI-compatible /chat/completions endpoint: OpenAI,
                Together, or a LOCAL Ollama / LM Studio server (no cloud, no key).
  * heuristic — rule-based, NO LLM and NO key. Lower quality, but it means the
                server always starts and the whole pipeline (ingest -> facts ->
                supersession -> retrieval) is demoable with zero setup.

"auto" picks emergent if EMERGENT_LLM_KEY + the package are present, else openai
if EXTRACTION_API_KEY is set, else heuristic. Any backend error falls back to
heuristic rather than dropping the message.
"""
import os
import re
import json
import logging

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

VALID_TYPES = {
    "identity", "preference", "health", "finance", "contact",
    "goal", "relationship", "location", "work", "skill", "other",
}
HIGH_STAKES_TYPES = {"health", "finance", "contact"}

SYSTEM_PROMPT = """You are a precise memory fact extractor for a personal AI memory vault.
Given a message, extract durable, reusable facts about the user (not transient chit-chat).

Rules:
- Only extract stable, useful facts (identity, preferences, goals, relationships, health, finance, contact info, location, work, skills).
- Do NOT extract questions, opinions about others, or ephemeral statements.
- Each fact must have a stable snake_case "key" so future updates to the same attribute can supersede it (e.g. "favorite_language", "employer", "home_city").
- "value" is the concise canonical value.
- "confidence" is 0.0-1.0 for how certain the statement asserts this fact.
- "high_stakes" is true for health conditions, financial/account/money details, or contact details (email/phone/address) that should require human confirmation.

Return ONLY a JSON object of this exact shape, no prose, no markdown fences:
{"facts": [{"type": "<one of: identity, preference, health, finance, contact, goal, relationship, location, work, skill, other>", "key": "<snake_case>", "value": "<string>", "confidence": <float>, "high_stakes": <bool>}]}
If nothing worth remembering, return {"facts": []}."""


def _parse_json(text: str):
    if not text:
        return {"facts": []}
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1] if t.count("```") >= 2 else t.strip("`")
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1:
        t = t[start:end + 1]
    try:
        return json.loads(t)
    except Exception:
        logger.warning("Extractor could not parse JSON: %r", text[:400])
        return {"facts": []}


def _normalize(facts):
    out = []
    for f in facts or []:
        try:
            ftype = str(f.get("type", "other")).lower().strip()
            if ftype not in VALID_TYPES:
                ftype = "other"
            key = str(f.get("key", "")).lower().strip().replace(" ", "_")
            value = str(f.get("value", "")).strip()
            if not key or not value:
                continue
            conf = float(f.get("confidence", 0.6))
            conf = max(0.0, min(1.0, conf))
            high = bool(f.get("high_stakes", False)) or ftype in HIGH_STAKES_TYPES
            out.append({
                "type": ftype, "key": key, "value": value,
                "confidence": round(conf, 3), "high_stakes": high,
            })
        except Exception:
            continue
    return out


# ---------------- Backend: Emergent (lazy import) ----------------
async def _run_emergent(text, role):
    from emergentintegrations.llm.chat import LlmChat, UserMessage  # lazy: optional dep
    primary_provider = os.environ.get("EXTRACTION_MODEL_PROVIDER", "anthropic")
    primary_model = os.environ.get("EXTRACTION_MODEL", "claude-opus-4-5-20251101")
    fb_provider = os.environ.get("FALLBACK_MODEL_PROVIDER", "gemini")
    fb_model = os.environ.get("FALLBACK_MODEL", "gemini-3-flash-preview")
    prompt = f"Message role: {role}\nMessage:\n{text}\n\nExtract facts as JSON."

    async def _call(provider, model):
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id="extractor",
                       system_message=SYSTEM_PROMPT).with_model(provider, model)
        resp = await chat.send_message(UserMessage(text=prompt))
        return _normalize(_parse_json(resp).get("facts", [])), model

    try:
        return await _call(primary_provider, primary_model)
    except Exception as e:
        logger.warning("Primary extractor failed (%s), falling back: %s", primary_model, e)
        return await _call(fb_provider, fb_model)


# ---------------- Backend: OpenAI-compatible ----------------
def _run_openai(text, role):
    import requests
    base = os.environ.get("EXTRACTION_API_BASE", "https://api.openai.com/v1").rstrip("/")
    key = os.environ.get("EXTRACTION_API_KEY", "")
    model = os.environ.get("EXTRACTION_MODEL", "gpt-4o-mini")
    resp = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Message role: {role}\nMessage:\n{text}\n\nExtract facts as JSON."},
            ],
        },
        timeout=float(os.environ.get("EXTRACTION_TIMEOUT", "30")),
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return _normalize(_parse_json(content).get("facts", [])), model


# ---------------- Backend: heuristic (no LLM, no key) ----------------
# (regex, type, stable snake_case key, high_stakes). Case-sensitive: proper-noun
# captures rely on capitalization; sentence starts accept "I"/"i".
_HEURISTIC_RULES = [
    (r"[Mm]y name is ([A-Z][a-zA-Z'’\-]+(?: [A-Z][a-zA-Z'’\-]+)?)", "identity", "full_name", False),
    (r"[Ii] (?:moved|relocated) to ([A-Z][a-zA-Z .'\-]+)", "location", "home_city", False),
    (r"[Ii](?:'m| am) (?:now )?(?:living|based) in ([A-Z][a-zA-Z .'\-]+)", "location", "home_city", False),
    (r"[Ii] live in ([A-Z][a-zA-Z .'\-]+)", "location", "home_city", False),
    (r"[Ii](?:'m| am) allergic to ([a-zA-Z][a-zA-Z .'\-]+)", "health", "allergy", True),
    (r"[Ii](?:'m| am)(?: a)? (vegetarian|vegan|pescatarian|pescetarian)", "health", "diet", False),
    (r"\bwork(?:ing)? at ([A-Z][a-zA-Z0-9 .&'\-]+)", "work", "employer", False),
    (r"[Ii](?:'m| am) an? ([a-z][a-zA-Z ]+?)(?: based| who| and|[.,]|$)", "work", "profession", False),
    (r"[Ii] (?:strongly )?(?:prefer|like) ([A-Za-z0-9+#]+)", "preference", "preference", False),
]

_STOP = re.compile(r"\b(last|this|next|and|but|who|which|because|since|when|so|for)\b", re.I)


def _clean_value(v):
    v = (v or "").strip().strip(".,;:!—-").strip()
    m = _STOP.search(v)
    if m:
        v = v[:m.start()].strip()
    v = re.sub(r"\s+", " ", v)
    return v if 0 < len(v) <= 40 else ""


def _run_heuristic(text, role):
    facts = []
    for pattern, ftype, key, high in _HEURISTIC_RULES:
        m = re.search(pattern, text)
        if not m:
            continue
        value = _clean_value(m.group(1))
        if not value:
            continue
        facts.append({"type": ftype, "key": key, "value": value,
                      "confidence": 0.6, "high_stakes": high})
    return _normalize(facts), "heuristic"


# ---------------- Dispatch ----------------
def _resolve_backend():
    b = os.environ.get("EXTRACTION_BACKEND", "auto").lower()
    if b in ("emergent", "openai", "heuristic"):
        return b
    if EMERGENT_LLM_KEY:
        try:
            import emergentintegrations  # noqa: F401
            return "emergent"
        except Exception:
            pass
    if os.environ.get("EXTRACTION_API_KEY"):
        return "openai"
    return "heuristic"


async def extract_facts(text: str, role: str = "user"):
    """Extract typed facts with confidence. Returns (facts, model_label)."""
    backend = _resolve_backend()
    try:
        if backend == "emergent":
            return await _run_emergent(text, role)
        if backend == "openai":
            return _run_openai(text, role)
        return _run_heuristic(text, role)
    except Exception as e:
        logger.warning("Extraction backend '%s' failed (%s); using heuristic fallback.", backend, e)
        return _run_heuristic(text, role)
