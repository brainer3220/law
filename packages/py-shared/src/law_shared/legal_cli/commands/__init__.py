"""Command registrations for the law CLI."""

from __future__ import annotations

from argparse import _SubParsersAction

from . import ask, draft, mcp, opensearch, postgres, preview, research, serve, share_service, stats, workspace_service

__all__ = ["register"]


def register(subparsers: _SubParsersAction) -> None:
    """Register all CLI commands with *subparsers*."""

    preview.register(subparsers)
    stats.register(subparsers)
    ask.register(subparsers)
    research.register(subparsers)
    draft.register(subparsers)
    serve.register(subparsers)
    share_service.register(subparsers)
    workspace_service.register(subparsers)
    postgres.register(subparsers)
    opensearch.register(subparsers)
    mcp.register(subparsers)
