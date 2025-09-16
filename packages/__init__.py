"""Top-level package namespace for shared libraries."""

from .env import load_env

load_env()

__all__ = ["load_env"]

