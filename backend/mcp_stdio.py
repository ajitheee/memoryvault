#!/usr/bin/env python3
"""MemoryVault — local stdio MCP transport (fully-local, single-user).

Speaks MCP JSON-RPC 2.0 over stdin/stdout (newline-delimited), reusing the same
tool definitions and dispatch logic as the HTTP transport. Authenticated by the
MCP_TOKEN environment variable, which resolves to a vault.

Usage (e.g. in claude_desktop_config.json):
  {
    "mcpServers": {
      "memoryvault-local": {
        "command": "python",
        "args": ["/app/backend/mcp_stdio.py"],
        "env": { "MCP_TOKEN": "mv_...", "MONGO_URL": "mongodb://localhost:27017", "DB_NAME": "test_database", "EMERGENT_LLM_KEY": "sk-emergent-..." }
      }
    }
  }
"""
import os
import sys
import json
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from db import db  # noqa: E402
from mcp import TOOLS, _dispatch_tool, PROTOCOL_VERSION  # noqa: E402


def _write(msg):
    sys.stdout.write(json.dumps(msg, default=str) + "\n")
    sys.stdout.flush()


async def _resolve_vault():
    token = os.environ.get("MCP_TOKEN")
    if not token:
        return None
    user = await db.users.find_one({"mcp_token": token}, {"_id": 0})
    return user["id"] if user else None


async def _stdin_reader():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    return reader


async def main():
    vault_id = await _resolve_vault()
    reader = await _stdin_reader()
    sys.stderr.write(f"[memoryvault-stdio] ready (vault={'ok' if vault_id else 'UNAUTH'})\n")
    sys.stderr.flush()

    while True:
        raw = await reader.readline()
        if not raw:
            break
        line = raw.decode("utf-8").strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = req.get("method")
        rid = req.get("id")
        params = req.get("params") or {}

        if method and method.startswith("notifications/"):
            continue

        if method == "initialize":
            _write({"jsonrpc": "2.0", "id": rid, "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "memoryvault-stdio", "version": "1.0.0"},
            }})
        elif method == "ping":
            _write({"jsonrpc": "2.0", "id": rid, "result": {}})
        elif method == "tools/list":
            _write({"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            if not vault_id:
                _write({"jsonrpc": "2.0", "id": rid, "error": {"code": -32001, "message": "MCP_TOKEN env not set or invalid"}})
                continue
            name = params.get("name")
            args = params.get("arguments") or {}
            try:
                result = await _dispatch_tool(vault_id, name, args)
                _write({"jsonrpc": "2.0", "id": rid, "result": {
                    "content": [{"type": "text", "text": json.dumps(result, default=str)}],
                    "isError": False,
                }})
            except Exception as e:
                _write({"jsonrpc": "2.0", "id": rid, "result": {
                    "content": [{"type": "text", "text": f"Error: {e}"}],
                    "isError": True,
                }})
        else:
            _write({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Method not found: {method}"}})


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        pass
