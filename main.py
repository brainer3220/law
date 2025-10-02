"""Backward-compatible CLI shim."""

from __future__ import annotations

from packages.legal_cli.runner import main

__all__ = ["main"]


if __name__ == "__main__":  # pragma: no cover
    main()
