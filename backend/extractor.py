import os
import json
import logging
from emergentintegrations.llm.chat import LlmChat, UserMessage

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


async def _run(provider, model, text, role):
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id="extractor",
        system_message=SYSTEM_PROMPT,
    ).with_model(provider, model)
    prompt = f"Message role: {role}\nMessage:\n{text}\n\nExtract facts as JSON."
    resp = await chat.send_message(UserMessage(text=prompt))
    return _normalize(_parse_json(resp).get("facts", []))


async def extract_facts(text: str, role: str = "user"):
    """Extract typed facts with confidence. Claude primary, Gemini fallback."""
    if not EMERGENT_LLM_KEY:
        return [], "none"
    primary_provider = os.environ.get("EXTRACTION_MODEL_PROVIDER", "anthropic")
    primary_model = os.environ.get("EXTRACTION_MODEL", "claude-opus-4-5-20251101")
    fb_provider = os.environ.get("FALLBACK_MODEL_PROVIDER", "gemini")
    fb_model = os.environ.get("FALLBACK_MODEL", "gemini-3-flash-preview")
    try:
        facts = await _run(primary_provider, primary_model, text, role)
        return facts, primary_model
    except Exception as e:
        logger.warning("Primary extractor failed (%s), falling back: %s", primary_model, e)
        try:
            facts = await _run(fb_provider, fb_model, text, role)
            return facts, fb_model
        except Exception as e2:
            logger.error("Fallback extractor also failed: %s", e2)
            return [], "error"
