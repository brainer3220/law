"""
Public schemas for legal documents, sections, and chunks.

These models are intentionally minimal and Pydantic v2-compatible.
They capture IDs, hierarchy, provenance, anchors, and text fields
required by the contextual RAG pipeline.
"""

from .models import Anchor, Chunk, Document, Section, SourceType

__all__ = [
    "Anchor",
    "Chunk",
    "Document",
    "Section",
    "SourceType",
]

