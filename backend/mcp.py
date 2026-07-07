import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from db import db
import memory

logger = logging.getLogger(__name__)
mcp_router = APIRouter(prefix="/api/mcp", tags=["mcp"])

PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "search_memory",
        "description": "Person-tuned retrieval of active memory facts ranked by semantic similarity, recency, confidence and usage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "k": {"type": "integer", "description": "Number of results", "default": 8},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_profile",
        "description": "Return stable identity and preference facts about the user.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "save_memory",
        "description": "Ingest a message into the vault; extracts typed facts (high-stakes facts go to a pending confirmation queue).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "role": {"type": "string", "enum": ["user", "assistant", "system"], "default": "user"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "build_context_pack",
        "description": "Return a token-budgeted context string ready to prepend to a prompt.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "token_budget": {"type": "integer", "default": 1000},
            },
            "required": ["query"],
        },
    },
    {
        "name": "confirm_fact",
        "description": "Confirm a pending (high-stakes) fact by its id, promoting it to active.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "list_pending",
        "description": "List facts awaiting human confirmation.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


async def _resolve_vault(request: Request):
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else request.headers.get("X-MCP-Token")
    if not token:
        return None
    user = await db.users.find_one({"mcp_token": token}, {"_id": 0})
    return user["id"] if user else None


async def _dispatch_tool(vault_id: str, name: str, args: dict):
    if name == "search_memory":
        res = await memory.retrieve(vault_id, args.get("query", ""), int(args.get("k", 8)))
        return [{"id": f["id"], "type": f["type"], "key": f["key"], "value": f["value"],
                 "confidence": f["confidence"], "score": f["score"]} for f in res]
    if name == "get_profile":
        return await memory.get_profile(vault_id)
    if name == "save_memory":
        return await memory.save_memory(vault_id, args.get("text", ""),
                                        args.get("role", "user"), source="mcp")
    if name == "build_context_pack":
        return await memory.build_context_pack(vault_id, args.get("query", ""),
                                               int(args.get("token_budget", 1000)))
    if name == "confirm_fact":
        r = await memory.confirm_fact(vault_id, args.get("id", ""))
        return r or {"error": "fact not found"}
    if name == "list_pending":
        return await memory.list_pending(vault_id)
    raise ValueError(f"Unknown tool: {name}")


def _rpc_result(rpc_id, result):
    return {"jsonrpc": "2.0", "id": rpc_id, "result": result}


def _rpc_error(rpc_id, code, message):
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}


@mcp_router.post("")
@mcp_router.post("/")
async def mcp_endpoint(request: Request):
    """Streamable-HTTP MCP transport: JSON-RPC 2.0 over a single POST endpoint."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_rpc_error(None, -32700, "Parse error"), status_code=400)

    method = body.get("method")
    rpc_id = body.get("id")
    params = body.get("params") or {}

    # Notifications (no id) -> 202 accepted, no body
    if method and method.startswith("notifications/"):
        return JSONResponse({}, status_code=202)

    if method == "initialize":
        return JSONResponse(_rpc_result(rpc_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "memoryvault", "version": "1.0.0"},
        }))

    if method == "ping":
        return JSONResponse(_rpc_result(rpc_id, {}))

    if method == "tools/list":
        return JSONResponse(_rpc_result(rpc_id, {"tools": TOOLS}))

    if method == "tools/call":
        vault_id = await _resolve_vault(request)
        if not vault_id:
            return JSONResponse(_rpc_error(rpc_id, -32001, "Invalid or missing MCP token"), status_code=401)
        name = params.get("name")
        args = params.get("arguments") or {}
        try:
            result = await _dispatch_tool(vault_id, name, args)
            return JSONResponse(_rpc_result(rpc_id, {
                "content": [{"type": "text", "text": json.dumps(result, default=str)}],
                "isError": False,
            }))
        except Exception as e:
            logger.exception("MCP tool error")
            return JSONResponse(_rpc_result(rpc_id, {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True,
            }))

    return JSONResponse(_rpc_error(rpc_id, -32601, f"Method not found: {method}"))
