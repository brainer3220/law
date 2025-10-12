"""Backward-compatible CLI shim and Vercel app export."""

from __future__ import annotations

from packages.legal_cli.runner import main as cli_main
from packages.legal_tools.vercel_app import app

# Expose the CLI entry point for local usage.
main = cli_main

__all__ = ["main", "app"]


if __name__ == "__main__":  # pragma: no cover
    cli_main()
