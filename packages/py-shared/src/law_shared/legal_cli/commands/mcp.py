"""Model Context Protocol helper commands."""

from __future__ import annotations

from argparse import _SubParsersAction, Namespace
from pathlib import Path

from ..config import RuntimeConfig

__all__ = ["register"]


def register(subparsers: _SubParsersAction) -> None:
    mcp_c7 = subparsers.add_parser(
        "mcp-context7-docs", help="Fetch docs via Context7 MCP (optional)"
    )
    mcp_c7.add_argument(
        "library", help="Library name to resolve (e.g., 'requests', 'next.js')"
    )
    mcp_c7.add_argument("--topic", help="Optional topic focus", default=None)
    mcp_c7.add_argument(
        "--tokens", type=int, default=5000, help="Max tokens to retrieve"
    )
    mcp_c7.set_defaults(handler=_cmd_mcp_context7)

    mcp_ag = subparsers.add_parser(
        "mcp-ast-grep", help="Search code via ast-grep MCP (optional)"
    )
    mcp_ag.add_argument("pattern", help="Pattern or YAML rule text")
    mcp_ag.add_argument("--project", help="Project root (default: CWD)")
    mcp_ag.add_argument("--language", help="Language hint (e.g., python, typescript)")
    mcp_ag.add_argument("--max-results", type=int, default=50)
    mcp_ag.set_defaults(handler=_cmd_mcp_ast_grep)


def _cmd_mcp_context7(args: Namespace, _: RuntimeConfig) -> None:
    from law_shared.legal_tools.mcp_client import MCPUnavailable, context7_docs  # type: ignore

    try:
        output = context7_docs(
            args.library,
            topic=getattr(args, "topic", None),
            tokens=int(getattr(args, "tokens", 5000)),
        )
    except MCPUnavailable as exc:
        raise SystemExit(str(exc))
    print(output)


def _cmd_mcp_ast_grep(args: Namespace, _: RuntimeConfig) -> None:
    from law_shared.legal_tools.mcp_client import MCPUnavailable, ast_grep_find  # type: ignore

    project = getattr(args, "project", None) or str(Path.cwd())
    try:
        output = ast_grep_find(
            args.pattern,
            project_dir=project,
            language=getattr(args, "language", None),
            max_results=int(getattr(args, "max_results", 50)),
        )
    except MCPUnavailable as exc:
        raise SystemExit(str(exc))
    print(output)
