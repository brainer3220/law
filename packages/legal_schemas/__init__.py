"""Shared schema package for legal-llm-agent.

Exports Pydantic models used across services.
"""

from .models import (
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

