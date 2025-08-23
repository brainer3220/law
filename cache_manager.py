"""
Compatibility layer for CacheManager.

Adds legacy helper methods used by unit tests while delegating to the
shared implementation in `packages.legal_tools.ingest.cache_manager`.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

from packages.legal_tools.ingest.cache_manager import (
    CacheManager as _SharedCacheManager,
    cache_manager as _shared_cache_manager,
)


class CacheManager(_SharedCacheManager):
    def __init__(self, cache_dir: Path | str | None = None):
        if isinstance(cache_dir, str):
            cache_dir = Path(cache_dir)
        super().__init__(cache_dir=cache_dir)

    # Legacy helpers expected by tests
    def get_cache_path(self, name: str, ext: str) -> Path:
        return self.cache_dir / f"{name}.{ext}"

    def cache_exists(self, name: str, ext: str) -> bool:  # type: ignore[override]
        return self.get_cache_path(name, ext).exists()

    def save_cache(self, obj: Any, name: str, ext: str) -> bool:
        path = self.get_cache_path(name, ext)
        return self.save_pickle(obj, path)

    def clear_cache(self):  # type: ignore[override]
        deleted = 0
        for p in self.cache_dir.glob("*"):
            if p.suffix in {".pkl", ".index"} and p.is_file():
                p.unlink()
                deleted += 1
        return {"deleted_files_count": deleted}


# Backward-compatible global instance
cache_manager = CacheManager()

__all__ = ["CacheManager", "cache_manager"]
