from __future__ import annotations

import os
import json
import logging
import shutil
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)


class MCPUnavailable(RuntimeError):
    pass


def _ensure_mcp() -> None:
    try:
        import mcp  # type: ignore
        _ = mcp
    except Exception as e:
        raise MCPUnavailable(
            "MCP client library not installed. Install with `uv pip install mcp`."
        ) from e


@dataclass
class MCPServer:
    command: List[str]
    cwd: Optional[Path] = None
    env: Optional[Dict[str, str]] = None


@contextmanager
def mcp_session(server: MCPServer):
    """Open an MCP stdio session to a server binary.

    Requires `mcp` Python package and a valid server executable (e.g., `context7-mcp`, `ast-grep-mcp`).
    """
    _ensure_mcp()
    from mcp.client.stdio import StdioServerTransport  # type: ignore
    from mcp.client.session import ClientSession  # type: ignore

    env = os.environ.copy()
    if server.env:
        env.update(server.env)
    transport = StdioServerTransport.create(server.command, cwd=str(server.cwd) if server.cwd else None, env=env)
    session = ClientSession(transport)
    try:
        session.open()
        yield session
    finally:
        try:
            session.close()
        except Exception:
            pass


def _find_command(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def context7_docs(library: str, *, topic: Optional[str] = None, tokens: int = 5000) -> str:
    """Fetch docs via Context7 MCP if configured.

    Env: CONTEXT7_MCP_CMD (default: `context7-mcp` if in PATH).
    Tools used: `resolve-library-id`, then `get-library-docs`.
    """
    cmd = os.getenv("CONTEXT7_MCP_CMD") or _find_command("context7-mcp")
    if not cmd:
        raise MCPUnavailable("Set CONTEXT7_MCP_CMD to your Context7 MCP server binary path.")

    server = MCPServer(command=[cmd])
    with mcp_session(server) as session:
        # resolve id
        try:
            resolve = session.call_tool("resolve-library-id", {"libraryName": library})
        except Exception as e:
            raise MCPUnavailable(f"Context7 MCP: tool resolve-library-id failed: {e}")
        lib_id = resolve.get("selectedLibraryId") or resolve.get("libraryId") or resolve.get("id")
        if not lib_id:
            # Some servers return a structured object; try common paths
            data = resolve.get("data") or resolve
            lib_id = (data.get("selected") or {}).get("id") if isinstance(data, dict) else None
        if not lib_id:
            raise MCPUnavailable("Context7 MCP: could not resolve library id.")

        # get docs
        try:
            docs = session.call_tool(
                "get-library-docs",
                {"context7CompatibleLibraryID": lib_id, "tokens": int(tokens), "topic": topic or ""},
            )
        except Exception as e:
            raise MCPUnavailable(f"Context7 MCP: tool get-library-docs failed: {e}")
        # Coerce to text
        return docs.get("content") or docs.get("text") or json.dumps(docs, ensure_ascii=False)


def ast_grep_find(pattern: str, *, project_dir: str, language: Optional[str] = None, max_results: int = 50) -> str:
    """Find code via ast-grep MCP if configured.

    Env: AST_GREP_MCP_CMD (default: `ast-grep-mcp` if in PATH).
    Tool: `find_code` (falls back to `find_code_by_rule` if needed).
    """
    cmd = os.getenv("AST_GREP_MCP_CMD") or _find_command("ast-grep-mcp")
    if not cmd:
        raise MCPUnavailable("Set AST_GREP_MCP_CMD to your ast-grep MCP server binary path.")
    server = MCPServer(command=[cmd])
    with mcp_session(server) as session:
        args: Dict[str, Any] = {
            "pattern": pattern,
            "project_folder": str(Path(project_dir).resolve()),
            "max_results": int(max_results),
        }
        if language:
            args["language"] = language
        try:
            res = session.call_tool("find_code", args)
        except Exception:
            # Try YAML rule path if server expects it
            res = session.call_tool("find_code_by_rule", {
                "yaml": pattern,
                "project_folder": str(Path(project_dir).resolve()),
                "max_results": int(max_results),
            })
        return res.get("text") or res.get("result") or json.dumps(res, ensure_ascii=False)

