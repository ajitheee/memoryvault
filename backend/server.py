import os
import json
import uuid
import asyncio
import logging

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Response
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from typing import List, Optional

from pydantic import BaseModel, Field

from db import db
from auth import auth_router, get_current_user, seed_admin, new_mcp_token
import memory
import ratelimit
import storage
from mcp import mcp_router

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="MemoryVault API")
api_router = APIRouter(prefix="/api")


# ---------- Schemas ----------
class SaveMemoryInput(BaseModel):
    text: str
    role: str = "user"


class ContextPackInput(BaseModel):
    query: str
    token_budget: int = Field(default=1000, ge=50, le=8000)


class SearchInput(BaseModel):
    query: str
    k: int = Field(default=8, ge=1, le=50)


class DecayInput(BaseModel):
    max_age_days: int = Field(default=60, ge=1)
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class FeedbackInput(BaseModel):
    fact_ids: List[str] = Field(min_length=1)
    verdict: str  # "helpful" | "correction"


class CorrectInput(BaseModel):
    new_value: Optional[str] = None


def vault_id_of(user: dict) -> str:
    return user["id"]


@api_router.get("/")
async def root():
    return {"service": "MemoryVault", "status": "ok"}


# ---------- Vault / stats ----------
@api_router.get("/vault/stats")
async def get_stats(user: dict = Depends(get_current_user)):
    return await memory.vault_stats(vault_id_of(user))


# ---------- Facts ----------
@api_router.get("/facts")
async def get_facts(status: str = "all", user: dict = Depends(get_current_user)):
    return await memory.list_facts(vault_id_of(user), status)


@api_router.get("/facts/{fact_id}")
async def get_fact(fact_id: str, user: dict = Depends(get_current_user)):
    f = await memory.get_fact(vault_id_of(user), fact_id)
    if not f:
        raise HTTPException(status_code=404, detail="Fact not found")
    return f


@api_router.post("/facts/{fact_id}/confirm")
async def confirm(fact_id: str, user: dict = Depends(get_current_user)):
    f = await memory.confirm_fact(vault_id_of(user), fact_id)
    if not f:
        raise HTTPException(status_code=404, detail="Fact not found")
    return f


@api_router.post("/facts/{fact_id}/reject")
async def reject(fact_id: str, user: dict = Depends(get_current_user)):
    ok = await memory.reject_fact(vault_id_of(user), fact_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Fact not found")
    return {"ok": True}


@api_router.post("/facts/{fact_id}/correct")
async def correct(fact_id: str, body: CorrectInput, user: dict = Depends(get_current_user)):
    r = await memory.correct_fact(vault_id_of(user), fact_id, body.new_value)
    if not r:
        raise HTTPException(status_code=404, detail="Fact not found")
    return r


@api_router.post("/feedback")
async def feedback(body: FeedbackInput, user: dict = Depends(get_current_user)):
    r = await memory.record_feedback(vault_id_of(user), body.fact_ids, body.verdict)
    if r.get("error"):
        raise HTTPException(status_code=400, detail=r["error"])
    return r


@api_router.get("/pending")
async def pending(user: dict = Depends(get_current_user)):
    return await memory.list_pending(vault_id_of(user))


@api_router.get("/profile")
async def profile(user: dict = Depends(get_current_user)):
    return await memory.get_profile(vault_id_of(user))


@api_router.get("/events")
async def events(user: dict = Depends(get_current_user)):
    return await memory.list_events(vault_id_of(user))


# ---------- Ingestion / retrieval ----------
@api_router.post("/memory/save")
async def save(body: SaveMemoryInput, user: dict = Depends(get_current_user)):
    ratelimit.check(f"save:{vault_id_of(user)}", 30, 60)
    return await memory.save_memory(vault_id_of(user), body.text, body.role)


@api_router.post("/memory/search")
async def search(body: SearchInput, user: dict = Depends(get_current_user)):
    return await memory.retrieve(vault_id_of(user), body.query, body.k)


@api_router.post("/context-pack")
async def context_pack(body: ContextPackInput, user: dict = Depends(get_current_user)):
    ratelimit.check(f"ctx:{vault_id_of(user)}", 60, 60)
    return await memory.build_context_pack(vault_id_of(user), body.query, body.token_budget)


# ---------- Maintenance ----------
@api_router.post("/decay")
async def decay(body: DecayInput, user: dict = Depends(get_current_user)):
    return await memory.run_decay(vault_id_of(user), body.max_age_days, body.min_confidence)


@api_router.post("/index/rebuild")
async def rebuild(user: dict = Depends(get_current_user)):
    return await memory.rebuild_index(vault_id_of(user))


@api_router.get("/export")
async def export(user: dict = Depends(get_current_user)):
    return await memory.export_vault(vault_id_of(user))


# ---------- Export bundles (object storage) ----------
@api_router.post("/export/bundle")
async def create_export_bundle(user: dict = Depends(get_current_user)):
    vid = vault_id_of(user)
    data = await memory.export_vault(vid)
    payload = json.dumps(data, indent=2, default=str).encode("utf-8")
    bundle_id = str(uuid.uuid4())
    path = f"{storage.APP_NAME}/exports/{vid}/{bundle_id}.json"
    try:
        result = await asyncio.to_thread(storage.put_object, path, payload, "application/json")
    except Exception as e:
        logger.error("Export bundle upload failed: %s", e)
        raise HTTPException(status_code=502, detail="Object storage unavailable")
    rec = {
        "id": bundle_id, "vault_id": vid, "storage_path": result["path"],
        "size": result.get("size", len(payload)),
        "facts": len(data["facts"]), "events": len(data["events"]),
        "created_at": memory.now_iso(), "is_deleted": False,
    }
    await db.export_bundles.insert_one(dict(rec))
    rec.pop("_id", None)
    return rec


@api_router.get("/export/bundles")
async def list_export_bundles(user: dict = Depends(get_current_user)):
    return await db.export_bundles.find(
        {"vault_id": vault_id_of(user), "is_deleted": False}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)


@api_router.get("/export/bundle/{bundle_id}/download")
async def download_export_bundle(bundle_id: str, user: dict = Depends(get_current_user)):
    rec = await db.export_bundles.find_one(
        {"id": bundle_id, "vault_id": vault_id_of(user), "is_deleted": False}, {"_id": 0}
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Bundle not found")
    content, _ = await asyncio.to_thread(storage.get_object, rec["storage_path"])
    return Response(
        content=content, media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="memoryvault-{bundle_id}.json"'},
    )


# ---------- MCP connection info ----------
@api_router.get("/mcp/info")
async def mcp_info(user: dict = Depends(get_current_user)):
    base = os.environ.get("PUBLIC_BASE_URL", "")
    return {
        "mcp_token": user.get("mcp_token"),
        "vault_id": user["id"],
        "http_endpoint": "/api/mcp",
        "note": "Use the token as Authorization: Bearer <token> for MCP tools/call.",
    }


@api_router.post("/mcp/token/regenerate")
async def regenerate_token(user: dict = Depends(get_current_user)):
    token = new_mcp_token()
    await db.users.update_one({"id": user["id"]}, {"$set": {"mcp_token": token}})
    return {"mcp_token": token}


app.include_router(auth_router)
app.include_router(api_router)
app.include_router(mcp_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    ip = ratelimit.client_ip(request)
    try:
        if path.startswith("/api/auth"):
            ratelimit.check(f"auth:{ip}", 30, 60)
        elif path.startswith("/api/mcp"):
            ratelimit.check(f"mcp:{ip}", 120, 60)
    except HTTPException as e:
        return JSONResponse({"detail": e.detail}, status_code=e.status_code, headers=e.headers or {})
    return await call_next(request)


async def decay_scheduler():
    interval = int(os.environ.get("DECAY_INTERVAL_SECONDS", "0"))
    if interval <= 0:
        return
    while True:
        await asyncio.sleep(interval)
        try:
            vaults = await db.users.distinct("id")
            total = 0
            for v in vaults:
                total += (await memory.run_decay(v)).get("archived", 0)
            logger.info("Scheduled decay archived %d fact(s) across %d vault(s)", total, len(vaults))
        except Exception as e:
            logger.error("Decay scheduler error: %s", e)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("mcp_token")
    await db.facts.create_index([("vault_id", 1), ("status", 1)])
    await db.facts.create_index([("vault_id", 1), ("type", 1), ("key", 1)])
    await db.events.create_index([("vault_id", 1), ("created_at", -1)])
    await db.export_bundles.create_index([("vault_id", 1), ("created_at", -1)])
    await seed_admin()
    try:
        await asyncio.to_thread(storage.init_storage)
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error("Object storage init failed: %s", e)
    asyncio.create_task(decay_scheduler())
    logger.info("MemoryVault startup complete")


@app.on_event("shutdown")
async def shutdown():
    from db import client
    client.close()
