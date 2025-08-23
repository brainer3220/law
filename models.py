"""Compatibility shim for Pydantic models.

Definitions live in `packages.legal_schemas.models` and are re-exported here
to keep imports stable while transitioning to the monorepo layout.
"""
import warnings
warnings.warn(
    "models.py is deprecated. Import from packages.legal_schemas.models instead (e.g., from packages.legal_schemas import QueryRequest).",
    DeprecationWarning,
    stacklevel=2,
)
from packages.legal_schemas.models import (  # noqa: F401
    QueryRequest,
    RetrievalResult,
    QueryResponse,
    ModelInfo,
    ModelManagerResponse,
    HealthResponse,
    StatsResponse,
    CacheResponse,
    ReloadResponse,
)

__all__ = [
    "QueryRequest",
    "RetrievalResult",
    "QueryResponse",
    "ModelInfo",
    "ModelManagerResponse",
    "HealthResponse",
    "StatsResponse",
    "CacheResponse",
    "ReloadResponse",
]
