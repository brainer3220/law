"""Helpers for loading `.env` files across the project."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Union

try:  # pragma: no cover - optional dependency
    from dotenv import find_dotenv, load_dotenv
except Exception:  # pragma: no cover - optional dependency
    def find_dotenv(*args, **kwargs):
        return ""

    def load_dotenv(*args, **kwargs):
        return False


PathLike = Union[str, Path]
_LOADED = False


def load_env(*, override: bool = False, extra_paths: Iterable[PathLike] | None = None) -> bool:
    """Load environment variables from `.env` files if they exist.

    Args:
        override: When ``True`` existing variables may be replaced.
        extra_paths: Optional iterable of additional files to load before the
            default search locations.

    Returns:
        ``True`` if any environment file was successfully loaded.
    """

    global _LOADED

    if _LOADED and not override and extra_paths is None:
        return True

    loaded_any = False
    loaded_paths: set[Path] = set()

    if extra_paths is not None:
        for raw_path in extra_paths:
            path = Path(raw_path).expanduser()
            if not path.exists():
                continue
            resolved = path.resolve()
            if resolved in loaded_paths:
                continue
            loaded_paths.add(resolved)
            loaded_any = load_dotenv(resolved, override=override) or loaded_any

    found = find_dotenv(usecwd=True)
    if found:
        resolved = Path(found).resolve()
        if resolved not in loaded_paths and resolved.exists():
            loaded_paths.add(resolved)
            loaded_any = load_dotenv(resolved, override=override) or loaded_any

    repo_dotenv = Path(__file__).resolve().parent.parent / ".env"
    if repo_dotenv.exists():
        resolved = repo_dotenv.resolve()
        if resolved not in loaded_paths:
            loaded_paths.add(resolved)
            loaded_any = load_dotenv(resolved, override=override) or loaded_any

    if not override:
        _LOADED = True

    return loaded_any


load_env()

