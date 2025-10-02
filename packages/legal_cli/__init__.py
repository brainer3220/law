"""CLI and service utilities for the law agent stack."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:  # pragma: no cover - fallback for editable installs
    __version__ = version("law")
except PackageNotFoundError:  # pragma: no cover - local development
    __version__ = "0.0.0"
