"""Compatibility wrapper for legacy imports.

Historically the shared Python utilities lived under a top-level
``packages`` module. The monorepo now exposes them via the
``law_shared`` package to make it consumable from the API app using
``uv``. We keep this wrapper so that older scripts importing
``packages`` continue to work while gradually migrating callers to the
new namespace.
"""

from law_shared import load_env

load_env()

__all__ = ["load_env"]
