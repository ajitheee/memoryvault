import os
import uuid
import logging

from fastapi import FastAPI, APIRouter, Depends, HTTPException
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db import db
from auth import auth_router, get_current_user, seed_admin, new_mcp_token, _public_user
import memory
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
    return await memory.save_memory(vault_id_of(user), body.text, body.role)


@api_router.post("/memory/search")
async def search(body: SearchInput, user: dict = Depends(get_current_user)):
    return await memory.retrieve(vault_id_of(user), body.query, body.k)


@api_router.post("/context-pack")
async def context_pack(body: ContextPackInput, user: dict = Depends(get_current_user)):
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


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("mcp_token")
    await db.facts.create_index([("vault_id", 1), ("status", 1)])
    await db.facts.create_index([("vault_id", 1), ("type", 1), ("key", 1)])
    await db.events.create_index([("vault_id", 1), ("created_at", -1)])
    await seed_admin()
    logger.info("MemoryVault startup complete")


@app.on_event("shutdown")
async def shutdown():
    from db import client
    client.close()
