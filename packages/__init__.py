"""Compatibility wrapper for legacy ``packages`` imports.

Historically the shared Python utilities lived under a top-level
``packages`` module. The monorepo now exposes them via the
``law_shared`` package to make it consumable from the API app using
``uv``. We keep this wrapper so that older scripts importing
``packages`` continue to work while gradually migrating callers to the
new namespace. This module makes the ``law_shared`` sources available
on ``sys.path`` and aliases its subpackages to their historical import
paths.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent
_PY_SHARED_SRC = _PACKAGE_ROOT / "py-shared" / "src"

if _PY_SHARED_SRC.exists():
    _shared_path = str(_PY_SHARED_SRC)
    if _shared_path not in sys.path:
        # Ensure the in-repo ``law_shared`` sources are importable even when
        # the package is not installed into the environment yet.
        sys.path.insert(0, _shared_path)

    _legacy_path = str(_PY_SHARED_SRC / "law_shared")
else:
    _legacy_path = None

__path__ = [str(_PACKAGE_ROOT)]
if _legacy_path is not None:
    __path__.append(_legacy_path)

if __spec__ is not None:
    __spec__.submodule_search_locations = __path__

law_shared = importlib.import_module("law_shared")
load_env = getattr(law_shared, "load_env")
load_env()

__all__ = ["load_env"]
