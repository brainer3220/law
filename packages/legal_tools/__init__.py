"""Utility tools for legal contextual RAG.

Exposes the ContextualChunker and interfaces for embeddings and indexing.
"""

from .contextual_rag import (
    ContextConfig,
    ContextualChunker,
    EmbeddingModel,
    IndexRecord,
)

__all__ = [
    "ContextConfig",
    "ContextualChunker",
    "EmbeddingModel",
    "IndexRecord",
]

