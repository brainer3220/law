"""Backward-compatible CLI shim and Vercel handler export."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from packages.legal_cli.runner import main as cli_main
from packages.legal_tools.api_server import ChatHandler

# Expose the CLI entry point for local usage.
main = cli_main

# Vercel's Python runtime expects a module-level `handler` subclassing BaseHTTPRequestHandler.
handler: type[BaseHTTPRequestHandler] = ChatHandler

__all__ = ["main", "handler"]


if __name__ == "__main__":  # pragma: no cover
    cli_main()
